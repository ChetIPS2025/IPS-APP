from __future__ import annotations

import html
import random
from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd
import streamlit as st

try:
    from app.auth import current_profile, current_role
    from app.branding import render_header
    from app.db import (
        create_signed_url,
        fetch_by_match_admin,
        fetch_table,
        fetch_table_admin,
        insert_row_admin,
        update_rows_admin,
        upload_bytes_admin,
    )
except ImportError:
    from auth import current_profile, current_role  # type: ignore
    from branding import render_header  # type: ignore
    from db import (  # type: ignore
        create_signed_url,
        fetch_by_match_admin,
        fetch_table,
        fetch_table_admin,
        insert_row_admin,
        update_rows_admin,
        upload_bytes_admin,
    )


_AUDITS = "tool_trailer_audits"
_AUDIT_ITEMS = "tool_trailer_audit_items"
_KIT_ITEMS = "asset_kit_items"


def _today() -> date:
    return datetime.utcnow().date()


def _as_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        s = str(v).strip()
        if not s:
            return default
        return float(s)
    except Exception:
        return default


def _audit_status_is_done(status: str) -> bool:
    return str(status or "").strip().lower() == "complete"


def _audit_overdue(due_date: Any, status: Any) -> bool:
    if _audit_status_is_done(str(status or "")):
        return False
    try:
        ds = str(due_date or "").strip()
        if not ds:
            return False
        d = date.fromisoformat(ds)
        return d < _today()
    except Exception:
        return False


def _render_audit_list(*, audits: list[dict], assets_by_id: dict[str, dict], emp_by_id: dict[str, str]) -> str | None:
    if not audits:
        st.info("No audits found.")
        return None

    rows = []
    for a in audits:
        aid = str(a.get("id") or "").strip()
        asset_id = str(a.get("asset_id") or "").strip()
        asset = assets_by_id.get(asset_id) or {}
        due = str(a.get("due_date") or "").strip() or "—"
        status = str(a.get("status") or "").strip() or "Pending"
        ass = str(a.get("assigned_to_employee_id") or "").strip()
        who = emp_by_id.get(ass) or "—"
        over = "Overdue" if _audit_overdue(a.get("due_date"), status) else ""
        rows.append(
            {
                "id": aid,
                "Trailer": f"{str(asset.get('asset_id') or '').strip()} — {str(asset.get('asset_name') or '').strip()}".strip(" —"),
                "Due": due,
                "Assigned to": who,
                "Status": status,
                "Overdue": over,
                "Frequency": str(a.get("frequency") or "").strip() or "—",
            }
        )
    df = pd.DataFrame(rows)
    st.dataframe(
        df.drop(columns=["id"], errors="ignore"),
        use_container_width=True,
        hide_index=True,
    )
    pick = st.selectbox(
        "Open audit",
        ["— Select —"] + [f"{r['Trailer']} · due {r['Due']} · {r['Status']}" for r in rows],
        key="tta_open_pick",
    )
    if pick and not pick.startswith("—"):
        idx = [f"{r['Trailer']} · due {r['Due']} · {r['Status']}" for r in rows].index(pick)
        return str(rows[idx]["id"])
    return None


def _upload_audit_item_photo(*, audit_id: str, audit_item_id: str, uploaded) -> str | None:
    if uploaded is None:
        return None
    data = uploaded.getvalue()
    if not data:
        return None
    ctype = str(getattr(uploaded, "type", "") or "").strip() or "image/jpeg"
    ext = "jpg"
    if "png" in ctype.lower():
        ext = "png"
    path = f"tool_trailer_audits/{audit_id}/{audit_item_id}.{ext}"
    try:
        upload_bytes_admin(path, data, content_type=ctype)
        return path
    except Exception:
        return None


def _render_audit_detail(*, audit: dict, items: list[dict], assets_by_id: dict[str, dict], emp_by_id: dict[str, str]) -> None:
    aud_id = str(audit.get("id") or "").strip()
    asset_id = str(audit.get("asset_id") or "").strip()
    asset = assets_by_id.get(asset_id) or {}
    title = f"{str(asset.get('asset_id') or '').strip()} — {str(asset.get('asset_name') or '').strip()}".strip(" —")
    st.markdown(f"### Audit · {html.escape(title)}")

    due = str(audit.get("due_date") or "").strip() or "—"
    status = str(audit.get("status") or "").strip() or "Pending"
    ass = str(audit.get("assigned_to_employee_id") or "").strip()
    who = emp_by_id.get(ass) or "—"
    st.caption(f"Due: **{due}** · Assigned to: **{who}** · Status: **{status}**")
    if _audit_overdue(audit.get("due_date"), status):
        st.warning("This audit is overdue.")

    if not items:
        st.info("No audit items found.")
        return

    all_ready = True
    for it in items:
        iid = str(it.get("id") or "").strip()
        if not iid:
            continue
        nm = str(it.get("item_name") or "").strip() or "—"
        req = _as_float(it.get("required_quantity"), 0)
        cur_status = str(it.get("status") or "").strip() or "Pending"
        photo_path = str(it.get("photo_url") or "").strip()
        vq = it.get("verified_quantity")
        notes = str(it.get("notes") or "").strip()

        with st.container(border=True):
            h1, h2, h3, h4 = st.columns([2.2, 0.9, 1.0, 1.1], gap="small")
            h1.markdown(f"**{html.escape(nm)}**")
            h2.caption(f"Expected: {req:g}")
            h3.caption(f"Status: {cur_status or '—'}")
            h4.caption("Photo ✅" if photo_path else "Photo required")

            c1, c2 = st.columns(2, gap="small")
            with c1:
                cam = st.camera_input("Take photo", key=f"tta_cam_{iid}")
            with c2:
                up = st.file_uploader("Upload photo", type=["jpg", "jpeg", "png"], key=f"tta_up_{iid}")

            uploaded = cam or up
            if uploaded is not None:
                pth = _upload_audit_item_photo(audit_id=aud_id, audit_item_id=iid, uploaded=uploaded)
                if pth:
                    update_rows_admin(_AUDIT_ITEMS, {"photo_url": pth}, {"id": iid})
                    st.success("Photo saved.")
                    st.rerun()
                else:
                    st.error("Could not save photo (storage).")

            if photo_path:
                url = create_signed_url(photo_path, expires_in=3600)
                if url:
                    st.image(url, width=240)

            s1, s2, s3 = st.columns([1, 1, 1], gap="small")
            vqty = s1.number_input(
                "Verified quantity",
                min_value=0.0,
                value=float(_as_float(vq, 0.0)) if vq is not None else 0.0,
                step=1.0,
                format="%.2f",
                key=f"tta_vq_{iid}",
            )
            st_opt = ["Pending", "Verified", "Missing", "Damaged"]
            idx = st_opt.index(cur_status) if cur_status in st_opt else 0
            st_new = s2.selectbox("Item status", st_opt, index=idx, key=f"tta_st_{iid}")
            n_new = s3.text_input("Notes", value=notes, key=f"tta_notes_{iid}")

            if st.button("Save item", type="secondary", use_container_width=True, key=f"tta_save_{iid}"):
                payload = {
                    "verified_quantity": float(vqty),
                    "status": str(st_new),
                    "notes": str(n_new or "").strip(),
                    "verified_at": datetime.utcnow().isoformat(),
                }
                update_rows_admin(_AUDIT_ITEMS, payload, {"id": iid})
                st.success("Saved.")
                st.rerun()

        # Completion gate (must have: status selected (not Pending), photo, verified quantity entered)
        eff_status = str(st_new or cur_status or "").strip()
        eff_photo = str(photo_path or "").strip()
        eff_vq = float(vqty)
        if eff_status == "Pending":
            all_ready = False
        if not eff_photo:
            all_ready = False
        if eff_vq <= 0:
            all_ready = False

    if any(str(it.get("status") or "").strip() in {"Missing", "Damaged"} for it in items):
        st.error("Alert: one or more items are marked Missing or Damaged.")

    if not _audit_status_is_done(status):
        if not all_ready:
            st.info("Audit cannot be marked Complete until every item has status, photo, and verified quantity.")
        if st.button("Mark audit Complete", type="primary", use_container_width=True, disabled=not all_ready, key="tta_complete"):
            update_rows_admin(
                _AUDITS,
                {"status": "Complete", "completed_at": datetime.utcnow().isoformat()},
                {"id": aud_id},
            )
            st.success("Audit completed.")
            st.rerun()


def render() -> None:
    render_header("Tool Trailer Audits")
    can_manage = current_role() in {"admin", "pm"}

    try:
        audits = fetch_table_admin(_AUDITS, limit=5000, order_by="due_date")
    except Exception as exc:
        st.warning(f"Audits are not available yet. Run migration **`sql/042_tool_trailer_audits.sql`**. ({exc})")
        return

    assets = fetch_table("assets", limit=5000, order_by="asset_name")
    assets_by_id = {str(a.get("id") or ""): a for a in assets or [] if a.get("id")}
    try:
        emp_rows = fetch_table("employees", columns="id,name", limit=4000, order_by="name")
    except Exception:
        emp_rows = []
    emp_by_id = {str(e.get("id") or ""): str(e.get("name") or "").strip() for e in emp_rows if e.get("id")}

    # Create audit (from Asset Database context or general)
    if can_manage:
        with st.expander("Create audit", expanded=False):
            ctx_asset = str(st.session_state.get("tta_create_asset_id") or "").strip()
            trailer_opts = []
            for a in assets or []:
                if str(a.get("asset_type") or "").strip().lower() != "tool trailer":
                    continue
                aid = str(a.get("id") or "").strip()
                if not aid:
                    continue
                label = f"{str(a.get('asset_id') or '').strip()} — {str(a.get('asset_name') or '').strip()}".strip(" —")
                trailer_opts.append((aid, label))
            trailer_opts.sort(key=lambda x: x[1].lower())
            labels = [l for _, l in trailer_opts]
            by_label = {l: i for i, l in trailer_opts}
            default_label = next((l for aid, l in trailer_opts if aid == ctx_asset), labels[0] if labels else "")
            pick = st.selectbox("Tool trailer", labels, index=labels.index(default_label) if default_label in labels else 0, key="tta_c_trailer")
            asset_id = str(by_label.get(pick) or "").strip()

            freq = st.selectbox("Frequency", ["Weekly", "Monthly"], key="tta_c_freq")
            n_items = st.number_input("Random items to verify", min_value=1, value=10, step=1, key="tta_c_n")
            due = st.date_input("Due date", value=_today() + timedelta(days=7), key="tta_c_due")
            emp_names = ["— Unassigned —"] + [emp_by_id[eid] for eid in sorted(emp_by_id.keys(), key=lambda x: emp_by_id.get(x, ""))]
            emp_pick = st.selectbox("Responsible employee", emp_names, key="tta_c_emp")
            emp_rev = {v: k for k, v in emp_by_id.items()}
            emp_id = emp_rev.get(emp_pick) if emp_pick and not emp_pick.startswith("—") else None
            notes = st.text_area("Notes", height=72, key="tta_c_notes")

            if st.button("Create Audit", type="primary", use_container_width=True, key="tta_c_go"):
                if not asset_id:
                    st.error("Select a tool trailer.")
                    st.stop()
                kit_rows = fetch_by_match_admin(_KIT_ITEMS, {"parent_asset_id": asset_id}, limit=5000)
                active = [r for r in kit_rows if bool((r or {}).get("is_active", True))]
                if not active:
                    st.error("This trailer has no active kit items to audit.")
                    st.stop()
                k = int(n_items)
                k = min(k, len(active))
                chosen = random.sample(active, k=k)
                end = _today()
                start = end - (timedelta(days=7) if freq == "Weekly" else timedelta(days=31))
                aud_payload = {
                    "asset_id": asset_id,
                    "audit_period_start": start.isoformat(),
                    "audit_period_end": end.isoformat(),
                    "frequency": freq,
                    "assigned_to_employee_id": emp_id,
                    "status": "Pending",
                    "due_date": due.isoformat(),
                    "notes": str(notes or "").strip(),
                }
                try:
                    created = insert_row_admin(_AUDITS, aud_payload)
                except Exception as exc:
                    st.error(f"Could not create audit: {exc} — run **`sql/042_tool_trailer_audits.sql`**.")
                    st.stop()
                audit_id = str((created or {}).get("id") or "").strip()
                if not audit_id:
                    # Fallback: refetch most recent matching audit (best-effort)
                    recs = fetch_by_match_admin(_AUDITS, {"asset_id": asset_id, "due_date": due.isoformat()}, limit=5)
                    audit_id = str((recs[0] or {}).get("id") or "").strip() if recs else ""
                if not audit_id:
                    st.error("Audit created but could not resolve id.")
                    st.stop()

                for r in chosen:
                    kid = str(r.get("id") or "").strip()
                    if not kid:
                        continue
                    item_payload = {
                        "audit_id": audit_id,
                        "kit_item_id": kid,
                        "item_name": str(r.get("item_name") or "").strip() or "—",
                        "required_quantity": float(_as_float(r.get("quantity"), 1.0)),
                        "verified_quantity": None,
                        "photo_url": "",
                        "status": "Pending",
                        "notes": "",
                    }
                    insert_row_admin(_AUDIT_ITEMS, item_payload)

                st.session_state.pop("tta_create_asset_id", None)
                st.success("Audit created.")
                st.session_state["tta_open_audit_id"] = audit_id
                st.rerun()

    # Overdue warning strip
    n_over = sum(1 for a in audits if _audit_overdue(a.get("due_date"), a.get("status")))
    if n_over:
        st.warning(f"**Overdue audits:** {n_over}")

    open_id = st.session_state.get("tta_open_audit_id")
    if open_id:
        aud = fetch_by_match_admin(_AUDITS, {"id": str(open_id)}, limit=1)
        audit = aud[0] if aud else None
        if not audit:
            st.session_state.pop("tta_open_audit_id", None)
            st.rerun()
        items = fetch_by_match_admin(_AUDIT_ITEMS, {"audit_id": str(open_id)}, limit=5000)
        items.sort(key=lambda r: str(r.get("item_name") or ""), reverse=False)
        if st.button("← Back to audits", use_container_width=True, key="tta_back"):
            st.session_state.pop("tta_open_audit_id", None)
            st.rerun()
        _render_audit_detail(audit=audit, items=items, assets_by_id=assets_by_id, emp_by_id=emp_by_id)
        return

    # List view
    f1, f2, f3 = st.columns([1, 1, 1], gap="small")
    with f1:
        status = st.selectbox("Status", ["All", "Pending", "In Progress", "Complete", "Overdue"], key="tta_f_status")
    with f2:
        assignee = st.selectbox("Assigned to", ["All"] + [emp_by_id[eid] for eid in sorted(emp_by_id.keys(), key=lambda x: emp_by_id.get(x, ""))], key="tta_f_emp")
    with f3:
        show_mine = st.checkbox(
            "Show mine",
            value=False,
            help="Shows audits assigned to your employee id when that mapping exists.",
            key="tta_f_mine",
        )

    filtered = audits
    if status != "All":
        if status == "Overdue":
            filtered = [a for a in filtered if _audit_overdue(a.get("due_date"), a.get("status"))]
        else:
            filtered = [a for a in filtered if str(a.get("status") or "").strip() == status]
    if assignee != "All":
        rev = {v: k for k, v in emp_by_id.items()}
        eid = rev.get(assignee)
        if eid:
            filtered = [a for a in filtered if str(a.get("assigned_to_employee_id") or "").strip() == str(eid)]

    if show_mine:
        # Best-effort: some deployments may store employee_id on profiles, others may not.
        prof = current_profile() or {}
        my_emp = str(prof.get("employee_id") or "").strip()
        if my_emp:
            filtered = [a for a in filtered if str(a.get("assigned_to_employee_id") or "").strip() == my_emp]
        else:
            st.info("Your profile is not linked to an employee id; showing all audits.")

    picked = _render_audit_list(audits=filtered, assets_by_id=assets_by_id, emp_by_id=emp_by_id)
    if picked and st.button("Open selected audit", type="primary", use_container_width=True, key="tta_open_go"):
        st.session_state["tta_open_audit_id"] = str(picked)
        st.rerun()

