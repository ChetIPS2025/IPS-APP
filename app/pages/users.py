from __future__ import annotations

from datetime import datetime
import re

import pandas as pd
import streamlit as st

try:
    from app.config import settings
except ImportError:
    try:
        from config import settings  # type: ignore
    except Exception:
        settings = None  # type: ignore

try:
    from app.auth import current_role
    from app.branding import render_header
    from app.db import (
        delete_rows_admin,
        fetch_by_match_admin,
        fetch_one,
        fetch_table,
        fetch_table_admin,
        get_admin_client,
        invite_auth_user,
        list_auth_users_admin,
        resend_invite_by_email,
        update_auth_user_email_admin,
        update_rows,
        update_rows_admin,
    )
except ImportError:
    from auth import current_role  # type: ignore
    from branding import render_header  # type: ignore
    from db import (  # type: ignore
        delete_rows_admin,
        fetch_by_match_admin,
        fetch_one,
        fetch_table,
        fetch_table_admin,
        get_admin_client,
        invite_auth_user,
        list_auth_users_admin,
        resend_invite_by_email,
        update_auth_user_email_admin,
        update_rows,
        update_rows_admin,
    )

try:
    from app.ips_crud_list_styles import inject_ips_crud_list_styles, render_crud_list_subtitle
except ImportError:
    from ips_crud_list_styles import inject_ips_crud_list_styles, render_crud_list_subtitle  # type: ignore

_ROLE_OPTIONS: tuple[str, ...] = ("viewer", "employee", "manager", "admin")

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _norm_email(v: object) -> str:
    return " ".join(str(v or "").strip().lower().split())


def _email_domain_allowed(email: str) -> bool:
    em = _norm_email(email)
    if not em or "@" not in em:
        return False
    dom = em.split("@", 1)[1]
    allow = ""
    try:
        allow = str(getattr(settings, "allowed_email_domain", "") or getattr(settings, "company_email_domain", "") or "").strip().lower()  # type: ignore[attr-defined]
    except Exception:
        allow = ""
    if not allow:
        return True
    return dom == allow


def _repair_user_links() -> dict[str, int]:
    """
    Best-effort repair:
    - ensure there is a profiles row for every auth user id
    - if a profile exists by email with wrong id, re-link id to auth id (when possible)
    - normalize profiles.email to lower(email)
    """
    admin = get_admin_client()
    auth_users = list_auth_users_admin(page=1, per_page=500)
    # Index profiles by email + id
    prof_rows = fetch_table_admin(
        "profiles",
        columns="id,email,role,is_active,must_reset_password,created_at,full_name,employee_id",
        limit=5000,
        order_by="email",
    )
    by_id = {str(p.get("id") or "").strip(): p for p in (prof_rows or []) if str(p.get("id") or "").strip()}
    by_email: dict[str, dict] = {}
    for p in prof_rows or []:
        em = _norm_email(p.get("email"))
        if em and em not in by_email:
            by_email[em] = p

    repaired = 0
    created = 0
    normalized = 0
    skipped = 0
    failed = 0

    for u in auth_users or []:
        uid = str(u.get("id") or "").strip()
        em = _norm_email(u.get("email"))
        if not uid or not em:
            continue

        prof = by_id.get(uid)
        if prof:
            # Normalize email casing
            if _norm_email(prof.get("email")) != em:
                try:
                    update_rows_admin("profiles", {"email": em}, {"id": uid})
                    normalized += 1
                except Exception:
                    failed += 1
            continue

        # Profile missing by id: attempt link by email
        cand = by_email.get(em)
        if cand:
            old_id = str(cand.get("id") or "").strip()
            if not old_id:
                failed += 1
                continue
            # Try updating primary key id -> auth id (works only if DB allows)
            try:
                admin.table("profiles").update({"id": uid, "email": em}).eq("id", old_id).execute()
                repaired += 1
            except Exception:
                failed += 1
            continue

        # Create missing profile for this auth user
        payload = {
            "id": uid,
            "email": em,
            "role": "employee",
            "is_active": True,
            "must_reset_password": True,
        }
        try:
            admin.table("profiles").insert(payload).execute()
            created += 1
        except Exception:
            failed += 1

    return {
        "repaired": repaired,
        "created": created,
        "normalized": normalized,
        "skipped": skipped,
        "failed": failed,
    }


def _employees_has_email_column() -> bool:
    try:
        fetch_table("employees", columns="id,email", limit=1)
        return True
    except Exception:
        return False


def delete_auth_user(user_id: str):
    admin = get_admin_client()
    return admin.auth.admin.delete_user(user_id)


def _safe_update_profile_employee_id(*, profile_id: str, employee_id: str | None) -> None:
    """Update profiles.employee_id when column exists; raise a clear error otherwise."""
    try:
        update_rows_admin("profiles", {"employee_id": employee_id}, {"id": str(profile_id)})
    except Exception as exc:
        msg = str(exc).lower()
        if "employee_id" in msg and ("column" in msg or "does not exist" in msg):
            raise RuntimeError("Database missing `profiles.employee_id` column. Add migration then retry.") from exc
        raise


def _safe_update_employee_link_cols(*, employee_id: str, profile_id: str) -> None:
    """
    Best-effort: set one of employees.profile_id / employees.auth_user_id when the column exists.
    """
    for col in ("profile_id", "auth_user_id"):
        try:
            update_rows("employees", {col: str(profile_id)}, {"id": str(employee_id)})
            return
        except Exception:
            continue


def _safe_set_employee_email_if_blank(*, employee_id: str, email: str) -> None:
    if not _employees_has_email_column():
        return
    try:
        row = fetch_one("employees", {"id": str(employee_id)})
    except Exception:
        row = None
    cur = str((row or {}).get("email") or "").strip()
    if cur:
        return
    try:
        update_rows("employees", {"email": str(email).strip()}, {"id": str(employee_id)})
    except Exception:
        pass

def _fetch_profile_row(profile_id):
    from app.db import get_client
    supabase = get_client()

    res = supabase.table("profiles") \
        .select("*") \
        .eq("id", profile_id) \
        .single() \
        .execute()

    return res.data if res.data else None


def _fmt_ts(v: object) -> str:
    if v is None:
        return ""
    if isinstance(v, datetime):
        return v.isoformat(sep=" ", timespec="seconds")
    return str(v)


def render() -> None:
    render_header("Users")

    if current_role() != "admin":
        st.error("Unauthorized. Admin access required.")
        return

    inject_ips_crud_list_styles()
    render_crud_list_subtitle("Invite users, manage roles, deactivate accounts, and resend invites.")

    with st.container(border=True):
        # Prefer employee-linked invites to prevent "unlinked login accounts".
        # Admin/viewer can be invited without an employee (override).
        employees_has_email = _employees_has_email_column()
        try:
            emp_cols = "id,name,email" if employees_has_email else "id,name"
            emp_rows = list(fetch_table("employees", columns=emp_cols, limit=5000, order_by="name") or [])
        except Exception:
            emp_rows = []

        emp_opts: list[tuple[str, str]] = []
        for e in emp_rows:
            eid = str(e.get("id") or "").strip()
            if not eid:
                continue
            nm = str(e.get("name") or "").strip() or "—"
            em = str(e.get("email") or "").strip() if employees_has_email else ""
            label = f"{nm} · {em}" if em else nm
            emp_opts.append((eid, label))
        emp_opts.sort(key=lambda t: t[1].lower())
        emp_labels = ["— Select employee —"] + [l for _, l in emp_opts]
        emp_id_by_label = {l: eid for eid, l in emp_opts}

        c1, c2, c3, c4 = st.columns([2, 1, 1, 1.2], gap="small")
        picked_emp = c1.selectbox("Employee (recommended)", emp_labels, key="users_invite_emp_pick")
        invite_email = c2.text_input("Email (optional)", placeholder="name@company.com", key="users_invite_email")
        default_role = c3.selectbox("Default role", list(_ROLE_OPTIONS), index=_ROLE_OPTIONS.index("employee"))
        create_for_emp_clicked = c4.button(
            "Create Login for Employee",
            type="secondary",
            use_container_width=True,
            key="users_create_login_for_employee_btn",
        )

        allow_unlinked = st.checkbox(
            "Admin override: allow standalone login (no employee link)",
            value=False,
            help="Prefer linking to an employee to prevent unlinked accounts. Use only for admin/viewer or exceptional cases.",
            key="users_invite_allow_unlinked",
        )

        if create_for_emp_clicked:
            if not picked_emp or picked_emp.startswith("—"):
                st.error("Select an employee first.")
                st.stop()
            eid = emp_id_by_label.get(picked_emp)
            emp_row = next((e for e in emp_rows if str(e.get("id") or "").strip() == str(eid)), None) or {}
            raw_email = str(emp_row.get("email") or "").strip().lower()
            if not raw_email or "@" not in raw_email:
                st.error("Employee must have an email to create login")
                st.stop()
            email = raw_email.strip().lower()
            if "indfustrial" in email:
                st.warning("Check spelling of company domain (found 'indfustrial').")
            if not _email_domain_allowed(email):
                st.warning("Check spelling of company domain / allowed domains.")
            name = str(emp_row.get("name") or "").strip()
            emp_role = str(emp_row.get("role") or "employee").strip().lower() or "employee"
            if emp_role in {"pm", "estimator"}:
                emp_role = "manager"
            if emp_role not in _ROLE_OPTIONS:
                emp_role = "employee"

            existing = []
            try:
                existing = fetch_by_match_admin("profiles", {"email": email}, columns="id,email", limit=1)
            except Exception:
                existing = []
            if existing:
                st.warning("Email already exists")
                st.stop()

            try:
                invited = invite_auth_user(
                    email=email,
                    role=emp_role,
                    employee_id=str(eid),
                    require_employee_link=False,
                )
            except Exception as exc:
                st.error(f"Could not create login: {exc}")
                st.stop()

            # Ensure employee email is set (source of truth for linking)
            try:
                update_rows_admin("employees", {"email": email}, {"id": str(eid)})
            except Exception:
                pass

            st.success("Login created and invite sent")
            st.rerun()

        if st.button("Send Invite", type="primary", use_container_width=True, key="users_send_invite_btn"):
            try:
                role_norm = str(default_role or "employee").strip().lower()
                if role_norm in {"pm", "estimator"}:
                    role_norm = "manager"
                employee_id = emp_id_by_label.get(picked_emp) if picked_emp and not picked_emp.startswith("—") else None
                email = str(invite_email or "").strip().lower()
                if employee_id and employees_has_email:
                    # Use employee email as source of truth when possible.
                    emp_row = next((e for e in emp_rows if str(e.get("id") or "").strip() == str(employee_id)), None) or {}
                    emp_email = str(emp_row.get("email") or "").strip().lower()
                    if emp_email:
                        email = emp_email
                if not email:
                    st.error("Email is required (or select an employee with an email).")
                    st.stop()
                if "indfustrial" in email:
                    st.warning("Check spelling of company domain (found 'indfustrial').")
                if not _email_domain_allowed(email):
                    st.warning("Check spelling of company domain / allowed domains.")
                require_emp = not (allow_unlinked or role_norm in {"admin", "viewer"})
                invited = invite_auth_user(
                    email=email,
                    role=str(role_norm),
                    employee_id=str(employee_id) if employee_id else None,
                    require_employee_link=bool(require_emp),
                )
                st.success(f"Invite sent to {invited.get('email')}.")
                st.rerun()
            except Exception as exc:
                st.error("Could not send invite.")
                with st.expander("Technical details"):
                    st.code(repr(exc), language="text")

    try:
        rows = fetch_table_admin(
            "profiles",
            columns="id,email,phone_number,role,created_at,must_reset_password,is_active",
            limit=2000,
            order_by="email",
        )
    except Exception as exc:
        # Back-compat: phone_number column may not exist yet.
        try:
            rows = fetch_table_admin(
                "profiles",
                columns="id,email,role,created_at,must_reset_password,is_active",
                limit=2000,
                order_by="email",
            )
        except Exception:
            st.error("Could not load profiles. Check SUPABASE_SERVICE_ROLE_KEY and database permissions.")
            with st.expander("Technical details"):
                st.code(repr(exc), language="text")
            return

    df = pd.DataFrame(rows)
    if df.empty:
        st.info("No users found.")
        return

    # Display table per spec: email, role, created_at
    view = df.copy()
    if "created_at" in view.columns:
        view["created_at"] = view["created_at"].map(_fmt_ts)
    for col in ("email", "role", "created_at"):
        if col not in view.columns:
            view[col] = ""
    if "phone_number" not in view.columns:
        view["phone_number"] = ""

    st.caption("Edit role/active status below and click **Save changes**.")
    edited = st.data_editor(
        view[["email", "phone_number", "role", "created_at", "must_reset_password", "is_active", "id"]],
        hide_index=True,
        use_container_width=True,
        disabled=["email", "created_at", "id"],
        column_config={
            "phone_number": st.column_config.TextColumn("phone_number"),
            "role": st.column_config.SelectboxColumn("role", options=list(_ROLE_OPTIONS), required=True),
            "must_reset_password": st.column_config.CheckboxColumn("must_reset_password"),
            "is_active": st.column_config.CheckboxColumn("is_active"),
            "id": st.column_config.TextColumn("id", disabled=True),
        },
        key="users_profiles_editor",
    )

    with st.expander("Edit login email (Supabase Auth)", expanded=False):
        st.caption("This updates **Auth** first, then syncs `public.profiles.email`.")
        id_to_email = {str(r.get("id") or ""): str(r.get("email") or "").strip().lower() for r in rows if r.get("id")}
        user_ids = [uid for uid in id_to_email.keys() if uid]
        user_ids.sort(key=lambda uid: id_to_email.get(uid, ""))
        pick_labels = [f"{id_to_email.get(uid, '')} · {uid[:8]}…" for uid in user_ids]
        picked = st.selectbox("User", pick_labels, key="users_edit_email_pick")
        picked_id = ""
        if picked:
            idx = pick_labels.index(picked)
            picked_id = user_ids[idx]
        cur_em = id_to_email.get(picked_id, "")
        new_em = st.text_input("New email", value=cur_em, key="users_edit_email_new")

        if st.button("Update email", type="primary", use_container_width=True, key="users_edit_email_go"):
            if current_role() != "admin":
                st.error("Unauthorized. Admin access required.")
                st.stop()
            uid = str(picked_id or "").strip()
            if not uid:
                st.error("Select a user.")
                st.stop()
            em = str(new_em or "").strip().lower()
            if not _EMAIL_RE.match(em):
                st.error("Enter a valid email address.")
                st.stop()
            # Uniqueness check (profiles mirror auth emails in this app)
            for pid, pemail in id_to_email.items():
                if pid != uid and str(pemail or "").strip().lower() == em:
                    st.error("That email is already used.")
                    st.stop()
            try:
                update_auth_user_email_admin(user_id=uid, new_email=em)
            except Exception as exc:
                msg = str(exc)
                if "already" in msg.lower() and "email" in msg.lower():
                    st.error("That email is already used.")
                else:
                    st.error("Could not update auth email.")
                    with st.expander("Technical details"):
                        st.code(repr(exc), language="text")
                st.stop()
            try:
                update_rows_admin("profiles", {"email": em}, {"id": uid})
            except Exception as exc:
                st.warning("Auth email updated, but syncing profiles.email failed.")
                with st.expander("Technical details"):
                    st.code(repr(exc), language="text")
            st.success("Email updated.")
            st.rerun()

    with st.expander("Delete Login Account (Supabase Auth)", expanded=False):
        st.caption("Deletes the user from **Supabase Auth** (`auth.users`). This cannot be undone.")
        try:
            auth_users = list_auth_users_admin(page=1, per_page=500)
        except Exception as exc:
            st.error(f"Could not load auth users: {exc}")
            auth_users = []
        auth_users = [u for u in auth_users if str(u.get("id") or "").strip()]
        auth_users.sort(key=lambda u: str(u.get("email") or u.get("phone") or "").lower())

        labels: list[str] = []
        id_by_label: dict[str, str] = {}
        for u in auth_users:
            uid = str(u.get("id") or "").strip()
            em = str(u.get("email") or "").strip()
            ph = str(u.get("phone") or "").strip()
            label = f"{em or ph or '—'} · {uid[:8]}…"
            labels.append(label)
            id_by_label[label] = uid

        picked = st.selectbox("Login account", options=["(select)"] + labels, key="selected_login_id")
        user_id = ""
        if picked and picked != "(select)":
            user_id = id_by_label.get(picked, "")

        if st.button(
            "Delete Login Account",
            type="secondary",
            use_container_width=True,
            disabled=current_role() != "admin" or not user_id,
            key="users_delete_login_go",
        ):
            # Temporary debug safety (requested)
            st.write("Deleting:", user_id)
            try:
                # Must use auth.users.id (not profiles.id / employee id)
                delete_auth_user(user_id)
                delete_rows_admin("profiles", {"id": user_id})
                st.success("Login account deleted")
                st.rerun()
            except Exception as e:
                st.error(f"Delete failed: {e}")

    with st.expander("Repair User Links", expanded=False):
        st.caption("Best-effort tool to fix mismatches between **auth.users** and **public.profiles** by email.")
        if st.button("Repair User Links", type="primary", use_container_width=True, key="users_repair_links_go"):
            try:
                res = _repair_user_links()
                st.success(
                    f"Repaired: {res.get('repaired', 0)} · Created: {res.get('created', 0)} · "
                    f"Normalized: {res.get('normalized', 0)} · Failed: {res.get('failed', 0)}"
                )
                st.rerun()
            except Exception as exc:
                st.error(f"Repair failed: {exc}")

    with st.expander("Link login accounts to employees", expanded=False):
        st.caption("Links `public.profiles` login accounts to `public.employees` safely (prevents mismatches).")

        # Load employees
        employees_has_email = _employees_has_email_column()
        try:
            emp_cols = "id,name,email" if employees_has_email else "id,name"
            employees = list(fetch_table("employees", columns=emp_cols, limit=5000, order_by="name") or [])
        except Exception as exc:
            st.error(f"Could not load employees: {exc}")
            employees = []

        profiles = list(rows or [])

        # Derived link state (best-effort)
        prof_by_id = {str(p.get("id") or "").strip(): p for p in profiles if str(p.get("id") or "").strip()}
        emp_by_id = {str(e.get("id") or "").strip(): e for e in employees if str(e.get("id") or "").strip()}

        # Current links (if columns exist)
        prof_link_emp: dict[str, str] = {}
        emp_link_prof: dict[str, str] = {}
        for pid, p in prof_by_id.items():
            eid = str(p.get("employee_id") or "").strip()
            if eid:
                prof_link_emp[pid] = eid
                if eid not in emp_link_prof:
                    emp_link_prof[eid] = pid

        # Auto-link by email
        c0, c1 = st.columns([1, 1], gap="small")
        with c0:
            if st.button("Auto-Link by Email", type="primary", use_container_width=True, key="users_auto_link_email"):
                prof_by_email: dict[str, str] = {}
                for p in profiles:
                    pid = str(p.get("id") or "").strip()
                    em = _norm_email(p.get("email"))
                    if pid and em and em not in prof_by_email:
                        prof_by_email[em] = pid

                emp_by_email: dict[str, str] = {}
                for e in employees:
                    eid = str(e.get("id") or "").strip()
                    em = _norm_email(e.get("email")) if employees_has_email else ""
                    if eid and em and em not in emp_by_email:
                        emp_by_email[em] = eid

                linked = 0
                skipped = 0
                for em, pid in prof_by_email.items():
                    eid = emp_by_email.get(em)
                    if not eid:
                        continue
                    # Safety: only link if neither side is already linked
                    if pid in prof_link_emp or eid in emp_link_prof:
                        skipped += 1
                        continue
                    try:
                        _safe_update_profile_employee_id(profile_id=pid, employee_id=eid)
                        _safe_update_employee_link_cols(employee_id=eid, profile_id=pid)
                        _safe_set_employee_email_if_blank(employee_id=eid, email=em)
                        linked += 1
                    except Exception as exc:
                        st.error(f"Auto-link failed for {em}: {exc}")
                st.success(f"Auto-linked {linked} account(s). Skipped {skipped} due to existing links.")
                st.rerun()

        with c1:
            replace_ok = st.checkbox(
                "Allow replacement (override existing links)",
                value=False,
                key="users_link_replace_ok",
                help="When enabled, manual link can replace existing links (admin-only).",
            )

        st.divider()
        st.markdown("##### Manual link")

        # Manual selection
        prof_options: list[tuple[str, str]] = []
        for p in profiles:
            pid = str(p.get("id") or "").strip()
            em = str(p.get("email") or "").strip()
            if pid:
                prof_options.append((pid, f"{em or '—'} · {pid[:8]}…"))
        prof_options.sort(key=lambda t: t[1].lower())

        emp_options: list[tuple[str, str]] = []
        for e in employees:
            eid = str(e.get("id") or "").strip()
            nm = str(e.get("name") or "").strip()
            em = str(e.get("email") or "").strip() if employees_has_email else ""
            if eid:
                lab = f"{nm or '—'} · {em or 'no email'} · {eid[:8]}…" if employees_has_email else f"{nm or '—'} · {eid[:8]}…"
                emp_options.append((eid, lab))
        emp_options.sort(key=lambda t: t[1].lower())

        p_lab = [x[1] for x in prof_options]
        e_lab = [x[1] for x in emp_options]
        p_pick = st.selectbox("Login account (profile)", options=["(select)"] + p_lab, key="users_manual_pick_profile")
        e_pick = st.selectbox("Employee", options=["(select)"] + e_lab, key="users_manual_pick_employee")

        pid = prof_options[p_lab.index(p_pick)][0] if p_pick != "(select)" else ""
        eid = emp_options[e_lab.index(e_pick)][0] if e_pick != "(select)" else ""

        p_email = _norm_email(prof_by_id.get(pid, {}).get("email")) if pid else ""
        e_email = _norm_email(emp_by_id.get(eid, {}).get("email")) if (eid and employees_has_email) else ""

        if pid and eid:
            st.caption(f"Profile email: `{p_email or '—'}` · Employee email: `{e_email or '—'}`")
            mismatch = bool(p_email and e_email and p_email != e_email)
            if mismatch:
                st.warning("Emails do not match. Linking anyway can cause confusion; enable override to proceed.")

            # Safety checks
            existing_emp_for_profile = prof_link_emp.get(pid)
            existing_profile_for_emp = emp_link_prof.get(eid)
            if existing_emp_for_profile and existing_emp_for_profile != eid:
                st.warning(f"This login is already linked to a different employee: `{existing_emp_for_profile[:8]}…`")
            if existing_profile_for_emp and existing_profile_for_emp != pid:
                st.warning(f"This employee is already linked to a different login: `{existing_profile_for_emp[:8]}…`")

            confirm_override = st.checkbox(
                "Confirm override",
                value=False,
                key="users_manual_confirm_override",
                help="Required when emails mismatch or when replacing an existing link.",
            )

            can_link = True
            needs_override = mismatch or (
                (existing_emp_for_profile and existing_emp_for_profile != eid) or (existing_profile_for_emp and existing_profile_for_emp != pid)
            )
            if needs_override and not (replace_ok and confirm_override):
                can_link = False

            if st.button(
                "Link account to employee",
                type="primary",
                use_container_width=True,
                disabled=(current_role() != "admin") or (not pid) or (not eid) or (not can_link),
                key="users_manual_link_go",
            ):
                try:
                    _safe_update_profile_employee_id(profile_id=pid, employee_id=eid)
                    _safe_update_employee_link_cols(employee_id=eid, profile_id=pid)
                    if employees_has_email:
                        _safe_set_employee_email_if_blank(employee_id=eid, email=p_email)
                    st.success("Linked.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not link: {exc}")

        st.divider()
        st.markdown("##### Unlinked login accounts")
        unlinked_profiles: list[dict] = []
        for p in profiles:
            pid0 = str(p.get("id") or "").strip()
            if not pid0:
                continue
            if str(p.get("employee_id") or "").strip():
                continue
            unlinked_profiles.append(p)

        if not unlinked_profiles:
            st.info("No unlinked login accounts (by `profiles.employee_id`).")
        else:
            for p in unlinked_profiles:
                pid0 = str(p.get("id") or "").strip()
                em0 = str(p.get("email") or "").strip() or "—"
                rl0 = str(p.get("role") or "").strip() or "—"
                act0 = "Active" if bool(p.get("is_active", True)) else "Inactive"
                ca0 = _fmt_ts(p.get("created_at"))
                a, b, c, d, e = st.columns([2.2, 0.8, 0.9, 1.2, 1.5], gap="small")
                a.write(em0)
                b.write(rl0)
                c.write(act0)
                d.write(ca0)
                with e:
                    if st.button("Select for link", use_container_width=True, key=f"users_unlinked_pick_{pid0}"):
                        st.session_state["users_manual_pick_profile"] = f"{em0} · {pid0[:8]}…"
                        st.rerun()

        st.divider()
        st.markdown("##### Unlinked employees")
        unlinked_emps: list[dict] = []
        for e in employees:
            eid0 = str(e.get("id") or "").strip()
            if not eid0:
                continue
            if eid0 in emp_link_prof:
                continue
            unlinked_emps.append(e)
        if not unlinked_emps:
            st.info("No unlinked employees (by `profiles.employee_id`).")
        else:
            for e in unlinked_emps:
                eid0 = str(e.get("id") or "").strip()
                nm0 = str(e.get("name") or "").strip() or "—"
                em0 = str(e.get("email") or "").strip() if employees_has_email else ""
                left, right = st.columns([3, 1], gap="small")
                left.write(f"{nm0}" + (f" · {em0}" if em0 else ""))
                with right:
                    if st.button("Select for link", use_container_width=True, key=f"users_unlinked_emp_pick_{eid0}"):
                        # best-effort: set by matching label
                        target = next((lab for (eid, lab) in emp_options if eid == eid0), None)
                        if target:
                            st.session_state["users_manual_pick_employee"] = target
                        st.rerun()

    b1, b2 = st.columns([1, 1], gap="small")
    with b1:
        if st.button("Save changes", type="primary", use_container_width=True, key="users_save_changes"):
            try:
                # Compare row-by-row by id; apply only changed fields.
                base_by_id = {str(r.get("id")): r for r in rows if r.get("id")}
                changed = 0
                for _, erow in edited.iterrows():
                    uid = str(erow.get("id") or "").strip()
                    if not uid or uid not in base_by_id:
                        continue
                    before = base_by_id[uid]
                    new_role = str(erow.get("role") or "viewer").strip().lower()
                    if new_role in {"pm", "estimator"}:
                        new_role = "manager"
                    if new_role not in _ROLE_OPTIONS:
                        new_role = "viewer"
                    new_active = bool(erow.get("is_active", True))
                    new_mrpw = bool(erow.get("must_reset_password", False))
                    new_phone = str(erow.get("phone_number") or "").strip() or None
                    payload = {}
                    if str(before.get("role") or "").strip().lower() != new_role:
                        payload["role"] = new_role
                    if bool(before.get("is_active", True)) != new_active:
                        payload["is_active"] = new_active
                    if bool(before.get("must_reset_password", False)) != new_mrpw:
                        payload["must_reset_password"] = new_mrpw
                    if "phone_number" in before and str(before.get("phone_number") or "").strip() != str(new_phone or ""):
                        payload["phone_number"] = new_phone
                    if payload:
                        # Temporary debug (requested)
                        st.write("Updating profile:", payload)
                        st.write("User ID:", uid)
                        try:
                            update_rows_admin("profiles", payload, {"id": uid})
                        except Exception as exc:
                            if "phone" in str(exc).lower() and ("column" in str(exc).lower() or "does not exist" in str(exc).lower()):
                                st.error("Could not save phone number — database is missing `profiles.phone_number`.")
                                st.stop()
                            st.error(f"Update failed: {exc}")
                            st.stop()
                        changed += 1
                if changed:
                    st.success("User updated")
                else:
                    st.info("No changes to save.")
                st.rerun()
            except Exception as exc:
                st.error(f"Update failed: {exc}")
    with b2:
        sel_email = st.text_input("Resend invite to email", placeholder="name@company.com", key="users_resend_email")
        if st.button("Resend invite", use_container_width=True, key="users_resend_invite_btn"):
            try:
                resend_invite_by_email(email=sel_email)
                st.success("Invite sent.")
            except Exception as exc:
                st.error("Could not resend invite.")
                with st.expander("Technical details"):
                    st.code(repr(exc), language="text")
