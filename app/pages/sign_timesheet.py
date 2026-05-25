from __future__ import annotations

import base64
from datetime import date, datetime, timedelta, timezone
from io import BytesIO
from typing import Any

import streamlit as st

try:
    from streamlit_drawable_canvas import st_canvas
except ImportError:  # pragma: no cover
    st_canvas = None  # type: ignore[misc, assignment]

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None  # type: ignore[misc, assignment]

try:
    from app.branding import render_header
    from app.db import create_signed_url, fetch_by_match_admin, fetch_table_admin, update_rows_admin, upload_bytes_admin
    from app.device_label import request_user_agent
    from app.services.job_weekly_timesheets import build_timesheet_pdf_bytes, week_bounds
    from app.services.job_service import job_row_select_label
except ImportError:
    from branding import render_header  # type: ignore
    from db import create_signed_url, fetch_by_match_admin, fetch_table_admin, update_rows_admin, upload_bytes_admin  # type: ignore
    from device_label import request_user_agent  # type: ignore
    from services.job_weekly_timesheets import build_timesheet_pdf_bytes, week_bounds  # type: ignore
    from services.job_service import job_row_select_label  # type: ignore


def _sig_b64(canvas_result) -> str | None:
    if canvas_result is None:
        return None
    img = getattr(canvas_result, "image_data", None)
    if img is None:
        return None
    if Image is None:
        return None
    try:
        im = Image.fromarray(img.astype("uint8"), mode="RGBA")
        buf = BytesIO()
        im.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception:
        return None


def render_public(sign_token: str) -> None:
    """
    Public signing flow (no login) invoked from main.py when `?tsign=<uuid>` is present.
    Uses admin server-side DB and storage access (does not require RLS exceptions).
    """
    tok = str(sign_token or "").strip()
    if not tok:
        render_header("Sign timesheet")
        st.error("Missing token.")
        return

    rows = fetch_by_match_admin("weekly_job_timesheets", {"sign_token": tok}, limit=1)
    ts_table = "weekly_job_timesheets"
    if not rows:
        rows = fetch_by_match_admin("job_weekly_timesheets", {"sign_token": tok}, limit=1)
        ts_table = "job_weekly_timesheets"
    if not rows:
        render_header("Sign timesheet")
        st.error("Timesheet not found or link is invalid.")
        return
    ts = rows[0]
    render_header("Sign Weekly Timesheet")

    status = str(ts.get("status") or "Draft").strip()
    if status == "Signed":
        st.success("This timesheet is already signed.")
    elif status == "Rejected":
        st.warning("This timesheet was rejected.")

    # Token expiry (sql/032): do not allow signing after expiry.
    exp_raw = str(ts.get("sign_token_expires_at") or "").strip()
    if exp_raw and status != "Signed":
        try:
            exp = datetime.fromisoformat(exp_raw.replace("Z", "+00:00"))
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > exp:
                st.error("This signing link has expired. Please request a new link.")
                status = "Expired"
        except ValueError:
            pass

    unsigned_path = str(ts.get("unsigned_pdf_url") or ts.get("pdf_file_url") or "").strip()
    signed_path = str(ts.get("signed_pdf_url") or ts.get("pdf_file_url") or "").strip()
    show_path = signed_path if signed_path and status == "Signed" else unsigned_path
    if show_path:
        try:
            url = create_signed_url(show_path, expires_in=3600)
        except Exception:
            url = ""
        if url:
            st.link_button("Open PDF", url)
            st.caption("PDF link expires (signed URL).")
        else:
            st.caption("PDF is not available.")

    # --- Header details + summary table ---
    job_rows = fetch_by_match_admin("jobs", {"id": ts.get("job_id")}, limit=1)
    job = job_rows[0] if job_rows else {"id": ts.get("job_id")}
    cust = None
    loc = None
    cid = str(ts.get("customer_id") or "").strip() or None
    clid = str(ts.get("customer_location_id") or "").strip() or None
    if cid:
        cr = fetch_by_match_admin("customers", {"id": cid}, limit=1)
        cust = cr[0] if cr else None
    if clid:
        lr = fetch_by_match_admin("customer_locations", {"id": clid}, limit=1)
        loc = lr[0] if lr else None

    ws_s = str(ts.get("week_start") or "").strip()[:10]
    we_s = str(ts.get("week_end") or "").strip()[:10]
    try:
        ws = date.fromisoformat(ws_s) if ws_s else date.today()
    except ValueError:
        ws = date.today()
    if not we_s:
        _, we_d = week_bounds(ws)
        we_s = we_d.isoformat()

    st.subheader("Timesheet")
    with st.container(border=True):
        st.markdown(f"**Job:** {job_row_select_label(job)}")
        st.markdown(f"**Customer:** {str((cust or {}).get('customer_name') or '—')}")
        loc_text = str((loc or {}).get("location_name") or (loc or {}).get("address") or "—")
        st.markdown(f"**Location:** {loc_text}")
        st.markdown(f"**Week:** {ws_s} to {we_s}")
        st.markdown(f"**Status:** {status}")

    # Build summary table from time_entries
    time_rows = fetch_table_admin("time_entries", limit=15000)
    def _d(x: Any) -> str:
        return str(x or "")[:10]
    time_rows = [
        r
        for r in time_rows
        if str(r.get("job_id") or "") == str(ts.get("job_id"))
        and ws_s <= _d(r.get("work_date")) <= we_s
    ]
    emp_rows = []
    try:
        emp_rows = fetch_table_admin("employees", columns="id,name", limit=5000, order_by="name")
    except Exception:
        emp_rows = []
    emp_name = {str(e.get("id")): str(e.get("name") or "").strip() for e in emp_rows if e.get("id")}

    # Employee x day grid
    grid: dict[str, dict[str, float]] = {}
    total_hours = 0.0
    for r in time_rows:
        wd = _d(r.get("work_date"))
        eid = str(r.get("employee_id") or "").strip()
        nm = emp_name.get(eid) or "Unknown"
        try:
            h = float(r.get("hours") or 0)
        except (TypeError, ValueError):
            h = 0.0
        if nm not in grid:
            grid[nm] = {}
        grid[nm][wd] = grid[nm].get(wd, 0.0) + h
        total_hours += h

    day_list = [ws + timedelta(days=i) for i in range(7)]
    cols = ["Employee"] + [d.strftime("%a %m/%d") for d in day_list] + ["Total"]
    rows_out = []
    for nm in sorted(grid.keys(), key=lambda s: s.lower()):
        row = {"Employee": nm}
        rt = 0.0
        for d in day_list:
            k = d.isoformat()
            v = float(grid.get(nm, {}).get(k, 0.0))
            rt += v
            row[d.strftime("%a %m/%d")] = v if v else 0.0
        row["Total"] = rt
        rows_out.append(row)
    if rows_out:
        import pandas as pd

        df = pd.DataFrame(rows_out)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.caption("No time entries found for this week.")
    st.markdown(f"**Total hours:** {total_hours:,.2f}")
    note = str(ts.get("work_performed") or ts.get("notes") or "").strip()
    if note:
        st.subheader("Work summary / notes")
        st.write(note)

    st.subheader("Sign")
    signer_name = st.text_input("Signed By Name", key="ts_sign_name")
    signer_email = st.text_input("Signed By Email (optional)", key="ts_sign_email")
    signer_title = st.text_input("Title (optional)", key="ts_sign_title", placeholder="Supervisor, PM, etc.")
    st.caption("Draw your signature below, then submit.")

    sig_b64 = None
    st.session_state.setdefault("_ts_canvas_ver", 0)
    if st_canvas is not None:
        if st.button("Clear signature", use_container_width=True, key="ts_sign_clear"):
            st.session_state["_ts_canvas_ver"] = int(st.session_state.get("_ts_canvas_ver") or 0) + 1
            st.rerun()
        canvas = st_canvas(
            fill_color="rgba(0,0,0,0)",
            stroke_width=3,
            stroke_color="#111827",
            background_color="#ffffff",
            height=160,
            width=520,
            drawing_mode="freedraw",
            key=f"ts_sign_canvas_{st.session_state.get('_ts_canvas_ver')}",
        )
        sig_b64 = _sig_b64(canvas)
    else:
        st.warning("Signature pad is unavailable (missing `streamlit-drawable-canvas`).")

    c1, c2 = st.columns(2, gap="small")
    with c1:
        submit = st.button("Submit signature", type="primary", use_container_width=True)
    with c2:
        reject = st.button("Reject", type="secondary", use_container_width=True)

    if reject:
        update_rows_admin(
            ts_table,
            {"status": "Rejected", "signed_at": datetime.now(timezone.utc).isoformat()},
            {"id": ts["id"]},
        )
        st.success("Rejected.")
        st.stop()

    if not submit:
        return

    if status == "Signed":
        st.info("Already signed.")
        return
    if status == "Expired":
        st.error("This signing link has expired. Please request a new link.")
        return
    if not signer_name.strip():
        st.error("Name is required.")
        st.stop()
    if signer_email.strip() and ("@" not in signer_email or "." not in signer_email.split("@")[-1]):
        st.error("Enter a valid email, or leave it blank.")
        st.stop()
    if not sig_b64:
        st.error("Signature is required.")
        st.stop()

    # Build signed PDF by regenerating with signature.
    if ts_table == "weekly_job_timesheets":
        try:
            from app.services.weekly_job_timesheet_service import (
                build_timesheet_pdf_bytes as build_wjt_pdf,
                load_timesheet_data,
            )
        except ImportError:
            from services.weekly_job_timesheet_service import (  # type: ignore
                build_timesheet_pdf_bytes as build_wjt_pdf,
                load_timesheet_data,
            )
        data = load_timesheet_data(str(ts["id"]))
        if not data:
            st.error("Could not load timesheet data.")
            st.stop()
        data.approved_by = signer_name.strip()
        sig_val = sig_b64 or ""
        if sig_val and not str(sig_val).startswith("data:"):
            sig_val = f"data:image/png;base64,{sig_val}"
        data.signature_data = sig_val
        data.signed_at = datetime.now(timezone.utc).isoformat()[:19]
        data.status = "Signed"
        signed_pdf = build_wjt_pdf(data)
        job_num = str(data.job_number or job.get("job_number") or "")[:32] or str(ts.get("job_id"))[:8]
        storage_path = f"weekly_job_timesheets/{job_num}/{ws_s}/signed.pdf"
    else:
        signed_pdf = build_timesheet_pdf_bytes(
            job=job,
            customer=cust,
            location=loc,
            week_start=date.fromisoformat(ws_s) if ws_s else datetime.now().date(),
            time_entries=time_rows,
            signer_name=signer_name.strip(),
            signer_email=signer_email.strip(),
            signer_title=signer_title.strip(),
            signature_data=sig_b64,
            work_summary=note,
            signed_at_utc=datetime.now(timezone.utc),
        )
        job_num = str(job.get("job_number") or job.get("job_id") or "").strip() or str(ts.get("job_id"))[:8]
        storage_path = f"job_timesheets/{job_num}/{ws_s}/signed.pdf"
    upload_bytes_admin(storage_path, signed_pdf, content_type="application/pdf")

    ua = request_user_agent()
    # Best-effort IP from headers.
    ip = ""
    try:
        hdrs = getattr(st.context, "headers", None)
        if hdrs is not None and hasattr(hdrs, "get"):
            ip = str(hdrs.get("x-forwarded-for") or hdrs.get("X-Forwarded-For") or "")[:120]
    except Exception:
        ip = ""
    sign_payload: dict[str, Any] = {
        "status": "Signed",
        "signed_at": datetime.now(timezone.utc).isoformat(),
        "signed_by_name": signer_name.strip()[:250],
        "signed_by_email": signer_email.strip()[:250],
        "signature_data": sig_b64,
        "pdf_file_url": storage_path,
        "signed_by_user_agent": str(ua or "")[:500],
        "signed_by_ip": ip,
    }
    if ts_table == "job_weekly_timesheets":
        sign_payload["signed_by_title"] = signer_title.strip()[:250]
        sign_payload["signed_pdf_url"] = storage_path
    else:
        sign_payload["approved_by"] = signer_name.strip()[:250]
    update_rows_admin(ts_table, sign_payload, {"id": ts["id"]})
    st.success("Signed. Thank you.")
    st.stop()

