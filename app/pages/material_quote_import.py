from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any

import pandas as pd
import streamlit as st

try:
    from auth import current_profile, current_role
    from branding import render_header
    from db import fetch_by_match_admin, fetch_table, fetch_table_admin, insert_row_admin, update_rows_admin, upload_bytes
    from services.material_quote_import import DEFAULT_MARKUP_PCT, compute_sell_price, extract_material_quote
    from services.materials_catalog_merge import (
        INVENTORY_MATERIALS_CATEGORY,
        inventory_row_to_material_catalog_shape,
        is_inventory_materials_category,
    )
    from services.estimate_materials_catalog import fetch_estimate_materials_catalog_rows
    from services.qr_codes import allocate_unique_inventory_qr_value, inventory_qr_from_item_id
except ImportError:
    from app.auth import current_profile, current_role  # type: ignore
    from app.ui.page_shell import render_page_header  # type: ignore
    from app.db import fetch_by_match_admin, fetch_table, fetch_table_admin, insert_row_admin, update_rows_admin, upload_bytes  # type: ignore
    from app.services.material_quote_import import DEFAULT_MARKUP_PCT, compute_sell_price, extract_material_quote  # type: ignore
    from app.services.materials_catalog_merge import (  # type: ignore
        INVENTORY_MATERIALS_CATEGORY,
        inventory_row_to_material_catalog_shape,
        is_inventory_materials_category,
    )
    from app.services.estimate_materials_catalog import fetch_estimate_materials_catalog_rows  # type: ignore
    from app.services.qr_codes import allocate_unique_inventory_qr_value, inventory_qr_from_item_id  # type: ignore


SESSION_QUEUE = "mq_upload_queue"
SESSION_ROWS = "mq_analysis_rows"
SESSION_IMPORTED = "mq_session_imported_total"

# Internal-only keys: omitted from the data editor; merged back from session after edits.
_MQ_EDITOR_HIDDEN = frozenset({"row_id", "vendor_item_number"})


def _material_quote_seed_row() -> dict[str, Any]:
    return {
        "row_id": str(uuid.uuid4()),
        "include": True,
        "vendor": "",
        "quote_number": "",
        "source_file": "",
        "item_description": "",
        "quantity": 0.0,
        "unit_cost": 0.0,
        "total": 0.0,
        "category": "",
        "subgroup": "",
        "unit": "EA",
        "material_item_key": "",
        "vendor_item_number": "",
        "notes": "",
        "duplicate_note": "",
    }


def clean_item_key(text: str) -> str:
    text = str(text).strip().upper()
    text = re.sub(r"[^A-Z0-9]+", "_", text)
    return text.strip("_")


def _finalize_inventory_qr_code(*, item_id: str) -> None:
    rid = str(item_id or "").strip()
    if not rid:
        return
    qv = allocate_unique_inventory_qr_value(
        fetch_by_match_admin=fetch_by_match_admin,
        item_id=rid,
        preferred=inventory_qr_from_item_id(rid),
        exclude_item_id=rid,
    )
    update_rows_admin("inventory_items", {"qr_code_value": qv}, {"id": rid})


def _insert_inventory_from_quote_line(
    *,
    description: str,
    subgroup: str,
    unit: str,
    unit_cost: float,
    final_item_key: str,
    vendor_item_number: str,
    vendor_name: str,
) -> dict[str, object]:
    notes_parts: list[str] = []
    if str(subgroup or "").strip():
        notes_parts.append(f"Subgroup: {str(subgroup).strip()}")
    if str(vendor_item_number or "").strip():
        notes_parts.append(f"Vendor #: {str(vendor_item_number).strip()}")
    notes = "\n".join(notes_parts).strip()

    payload: dict[str, object] = {
        "item_name": str(description or "").strip()[:2000],
        "category": INVENTORY_MATERIALS_CATEGORY,
        "unit": str(unit or "EA").strip() or "EA",
        "quantity_on_hand": 0.0,
        "reorder_point": 0.0,
        "unit_cost": float(unit_cost or 0) if float(unit_cost or 0) > 0 else None,
        "vendor": str(vendor_name or "").strip()[:500],
        "storage_location": "",
        "notes": notes[:8000] if notes else "",
        "is_active": True,
    }
    fk = str(final_item_key or "").strip()
    if fk:
        payload["sku"] = fk[:500]

    row = insert_row_admin("inventory_items", payload)
    rid = str(row.get("id") or "").strip()
    if rid and not str(row.get("qr_code_value") or "").strip():
        _finalize_inventory_qr_code(item_id=rid)
    fresh = fetch_by_match_admin("inventory_items", {"id": rid}, limit=1) if rid else []
    if fresh:
        return inventory_row_to_material_catalog_shape(fresh[0])
    return {
        "item_key": fk,
        "description": str(description or "").strip(),
        "category": INVENTORY_MATERIALS_CATEGORY,
        "inventory_id": "",
        "vendor_item_number": str(vendor_item_number or "").strip(),
        "_source": "inventory_items",
    }


def make_unique_item_key(base_key: str, rows: list[dict]) -> str:
    existing = {str(row.get("item_key", "")).strip().upper() for row in rows}
    if base_key.upper() not in existing:
        return base_key

    index = 2
    while True:
        candidate = f"{base_key}_{index}"
        if candidate.upper() not in existing:
            return candidate
        index += 1


def _storage_name(original_name: str) -> str:
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", original_name)
    return f"material_quotes/{stamp}_{safe_name}"


def _token_set(text: str) -> set[str]:
    text = re.sub(r"[^a-z0-9]+", " ", str(text).lower()).strip()
    return {t for t in text.split() if len(t) > 1}


def find_best_material_match(
    description: str,
    vendor_item_number: str,
    materials: list[dict],
) -> tuple[dict | None, float]:
    vin = str(vendor_item_number or "").strip().upper()
    if vin:
        for row in materials:
            if str(row.get("vendor_item_number") or "").strip().upper() == vin:
                return row, 1.0

    desc = str(description or "").strip().lower()
    if not desc:
        return None, 0.0

    desc_tokens = _token_set(desc)
    best_row: dict | None = None
    best_score = 0.0

    for row in materials:
        d = str(row.get("description", "") or "").strip().lower()
        ik = str(row.get("item_key", "") or "").strip().lower()
        inv = str(row.get("inventory_id", "") or "").strip().lower()

        score = 0.0
        cat_tokens = _token_set(" ".join([d, ik, inv]))
        if desc_tokens and cat_tokens:
            inter = len(desc_tokens & cat_tokens)
            union = len(desc_tokens | cat_tokens) or 1
            score = max(score, inter / union)

        if d:
            if desc == d:
                score = 1.0
            elif desc in d or d in desc:
                score = max(score, 0.65)
        if ik and (desc == ik or desc in ik or ik in desc):
            score = max(score, 0.55)

        if score > best_score:
            best_score = score
            best_row = row

    if best_row is not None and best_score >= 0.2:
        return best_row, min(1.0, best_score)
    return None, best_score


def _norm_vendor(v: str) -> str:
    return re.sub(r"\s+", " ", str(v or "").strip().lower())


def _norm_desc(v: str) -> str:
    return re.sub(r"\s+", " ", str(v or "").strip().lower())


def _dup_tuple_full(vendor: str, desc: str, qty: Any, unit_cost: Any) -> tuple[str, str, float, float]:
    try:
        q = round(float(qty or 0), 4)
    except (TypeError, ValueError):
        q = 0.0
    try:
        c = round(float(unit_cost or 0), 4)
    except (TypeError, ValueError):
        c = 0.0
    return (_norm_vendor(vendor), _norm_desc(desc), q, c)


def _inventory_dup_keys_materials() -> set[tuple[str, str, float]]:
    out: set[tuple[str, str, float]] = set()
    try:
        inv_rows = fetch_table("inventory_items", limit=5000)
    except Exception:
        return out
    for r in inv_rows or []:
        if not isinstance(r, dict) or not is_inventory_materials_category(r):
            continue
        vn = _norm_vendor(r.get("vendor"))
        nm = _norm_desc(r.get("item_name"))
        try:
            uc = round(float(r.get("unit_cost") or 0), 4)
        except (TypeError, ValueError):
            uc = 0.0
        out.add((vn, nm, uc))
    return out


def _mark_duplicate_flags(rows: list[dict], inv_keys: set[tuple[str, str, float]]) -> None:
    seen: set[tuple[str, str, float, float]] = set()
    for row in rows:
        tup = _dup_tuple_full(
            row.get("vendor", ""),
            row.get("item_description", ""),
            row.get("quantity"),
            row.get("unit_cost"),
        )
        flags: list[str] = []
        if tup in seen:
            flags.append("Duplicate row")
        seen.add(tup)
        inv_t = (tup[0], tup[1], tup[3])
        if inv_t in inv_keys:
            flags.append("Inventory match")
        row["duplicate_note"] = " · ".join(flags) if flags else ""


def _rows_from_extraction(*, result: dict[str, Any], source_name: str, materials: list[dict]) -> list[dict[str, Any]]:
    vendor = str(result.get("vendor_name", "") or "").strip()
    quote_number = str(result.get("quote_number", "") or "").strip()
    suggest_threshold = 0.35

    out: list[dict[str, Any]] = []
    for item in result.get("items") or []:
        unit_cost = float(item.get("unit_cost", 0) or 0)
        quantity = float(item.get("quantity", 0) or 0)
        extended_cost = float(item.get("extended_cost", quantity * unit_cost) or 0)
        desc = str(item.get("item_description", "") or "").strip()
        vin = str(item.get("vendor_item_number", "") or "").strip()
        match_row, match_score = find_best_material_match(desc, vin, materials)
        mat_key = ""
        if match_row is not None and match_score >= suggest_threshold:
            mat_key = str(match_row.get("item_key") or "").strip()

        out.append(
            {
                "row_id": str(uuid.uuid4()),
                "include": True,
                "vendor": vendor,
                "quote_number": quote_number,
                "source_file": source_name,
                "item_description": desc,
                "quantity": quantity,
                "unit_cost": unit_cost,
                "total": round(extended_cost, 2),
                "category": str(item.get("category", "") or "").strip(),
                "subgroup": str(item.get("subgroup", "") or "").strip(),
                "unit": str(item.get("unit", "EA") or "EA").strip() or "EA",
                "material_item_key": mat_key,
                "vendor_item_number": vin,
                "notes": str(item.get("notes", "") or "").strip(),
                "duplicate_note": "",
            }
        )
    return out


def _ensure_session_defaults() -> None:
    if SESSION_QUEUE not in st.session_state:
        st.session_state[SESSION_QUEUE] = []
    if SESSION_ROWS not in st.session_state:
        st.session_state[SESSION_ROWS] = []
    if SESSION_IMPORTED not in st.session_state:
        st.session_state[SESSION_IMPORTED] = 0
    if "mq_markup_pct" not in st.session_state:
        st.session_state["mq_markup_pct"] = float(DEFAULT_MARKUP_PCT) * 100.0
    st.session_state.pop("material_quote_result", None)
    st.session_state.pop("material_quote_file_meta", None)


def _category_material_options(materials: list[dict]) -> tuple[list[str], list[str]]:
    cats = sorted(
        {
            (str(m.get("category") or "").strip() or "Uncategorized")
            for m in materials
            if isinstance(m, dict) and str(m.get("item_key") or "").strip()
        }
    )
    cat_options = [""] + cats
    keys = sorted(
        {str(m.get("item_key") or "").strip() for m in materials if isinstance(m, dict) and str(m.get("item_key") or "").strip()},
        key=str.lower,
    )
    mat_options = [""] + keys
    return cat_options, mat_options


def _render_compact_queue() -> None:
    q = st.session_state[SESSION_QUEUE]
    if not q:
        return
    st.markdown(
        """
        <style>
        .mq-queue-row { font-size: 0.82rem; padding: 2px 0; border-bottom: 1px solid rgba(120,150,200,.22); }
        .mq-queue-status-waiting { opacity: 0.85; }
        .mq-queue-status-failed { color: #f88; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    for item in q:
        c1, c2, c3 = st.columns([3.2, 1.3, 0.9])
        with c1:
            st.markdown(
                f"<div class='mq-queue-row'>{item['name']} <small>({item['ext'].upper()})</small></div>",
                unsafe_allow_html=True,
            )
        with c2:
            status = item.get("status", "waiting")
            cls = "mq-queue-status-failed" if status == "failed" else "mq-queue-status-waiting"
            label = {"waiting": "Waiting", "analyzing": "Analyzing", "failed": "Failed", "complete": "Complete"}.get(
                status, status
            )
            st.markdown(f"<div class='mq-queue-row {cls}'>{label}</div>", unsafe_allow_html=True)
        with c3:
            if st.button("Remove", key=f"mq_rm_{item['id']}", use_container_width=True):
                st.session_state[SESSION_QUEUE] = [x for x in q if x["id"] != item["id"]]
                st.rerun()
        if status == "failed" and item.get("error"):
            st.caption(f"Error: {item['error'][:200]}")


def _merge_new_uploads(uploaded: list[Any]) -> None:
    if not uploaded:
        return
    sigs = {(x["name"], x["size"]) for x in st.session_state[SESSION_QUEUE]}
    for uf in uploaded:
        raw = uf.getvalue()
        name = str(uf.name or "upload")
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        sig = (name, len(raw))
        if sig in sigs:
            continue
        sigs.add(sig)
        st.session_state[SESSION_QUEUE].append(
            {
                "id": str(uuid.uuid4()),
                "name": name,
                "ext": ext,
                "bytes": raw,
                "size": len(raw),
                "status": "waiting",
                "error": "",
            }
        )


def _run_batch_analyze(materials: list[dict]) -> None:
    queue = list(st.session_state[SESSION_QUEUE])
    pending = [x for x in queue if x["status"] in ("waiting", "failed")]
    if not pending:
        st.warning("No files waiting for analysis.")
        return
    remaining: list[dict] = [x for x in queue if x not in pending]
    new_lines: list[dict] = []
    ok_files = 0
    with st.status("Analyzing uploads…", expanded=True) as status:
        for item in pending:
            status.write(f"Analyzing **{item['name']}**…")
            try:
                result = extract_material_quote(item["bytes"], item["name"])
                lines = _rows_from_extraction(result=result, source_name=item["name"], materials=materials)
                new_lines.extend(lines)
                ok_files += 1
                n = len(result.get("items") or [])
                status.write(f"**{item['name']}:** {n} line item(s) extracted.")
            except Exception as exc:
                item["status"] = "failed"
                item["error"] = str(exc)
                remaining.append(item)
                status.write(f"**{item['name']}** failed: {exc}")
        if ok_files:
            status.write(f"Done — {ok_files} file(s), {len(new_lines)} new row(s) in the table.")
    st.session_state[SESSION_QUEUE] = remaining
    st.session_state[SESSION_ROWS] = list(st.session_state[SESSION_ROWS]) + new_lines
    st.rerun()


def render_material_quote_import_form(return_to_materials: bool = False) -> None:
    """
    Render the vendor quote import form for adding Inventory: Materials.

    Multi-file vendor quote upload, batch AI extraction, combined grid, import to
    ``material_quotes`` / ``material_quote_items`` / ``inventory_items`` (Materials).
    """
    materials = fetch_estimate_materials_catalog_rows(
        fetch_table=fetch_table,
        fetch_table_admin=fetch_table_admin,
    )
    cat_options, mat_options = _category_material_options(materials)
    inv_dup_keys = _inventory_dup_keys_materials()
    _ensure_session_defaults()

    st.markdown(
        """
        <style>
        .mq-footer { display:flex; flex-wrap:wrap; gap:12px 18px; font-size:0.88rem; margin-top:8px;
          padding:8px 0; border-top:1px solid rgba(120,150,200,.28); }
        @media (max-width: 700px) { .mq-footer { flex-direction: column; } }
        </style>
        """,
        unsafe_allow_html=True,
    )

    uploaded_list = st.file_uploader(
        "Upload vendor quotes (PDF or image)",
        type=["pdf", "jpg", "jpeg", "png"],
        accept_multiple_files=True,
        help="Multiple files at once. After analysis, files leave the queue; only results remain.",
        key="mq_multi_uploader",
    )
    if uploaded_list:
        _merge_new_uploads(list(uploaded_list))

    col_a, col_b, col_c = st.columns([1, 1, 1])
    with col_a:
        if st.button("Analyze All Uploads", type="primary", use_container_width=True):
            _run_batch_analyze(materials)
    with col_b:
        if st.button("Clear upload queue", use_container_width=True):
            st.session_state[SESSION_QUEUE] = []
            st.rerun()
    with col_c:
        st.number_input(
            "Default markup %",
            min_value=0.0,
            step=1.0,
            key="mq_markup_pct",
        )

    with st.expander("Upload queue", expanded=bool(st.session_state[SESSION_QUEUE])):
        _render_compact_queue()

    rows = list(st.session_state[SESSION_ROWS])

    if st.button("Clear Analyzed Results", use_container_width=True):
        st.session_state[SESSION_ROWS] = []
        st.rerun()

    if not rows:
        return

    st.markdown("---")
    st.subheader("Combined results")

    df = pd.DataFrame(rows)
    editor_key = "mq_editor_embed" if return_to_materials else "mq_editor_main"

    vis_cols = [c for c in df.columns if c not in _MQ_EDITOR_HIDDEN]
    mq_column_order = [
        "include",
        "vendor",
        "source_file",
        "quote_number",
        "item_description",
        "quantity",
        "unit_cost",
        "total",
        "category",
        "material_item_key",
        "notes",
        "duplicate_note",
        "subgroup",
        "unit",
    ]
    editor_order = [c for c in mq_column_order if c in vis_cols]

    mq_column_config = {
        "include": st.column_config.CheckboxColumn("Include", default=True),
        "vendor": st.column_config.TextColumn("Vendor"),
        "source_file": st.column_config.TextColumn("Source file", disabled=True),
        "quote_number": st.column_config.TextColumn("Quote #"),
        "item_description": st.column_config.TextColumn("Description", width="medium"),
        "quantity": st.column_config.NumberColumn("Qty", format="%.4f"),
        "unit_cost": st.column_config.NumberColumn("Unit cost", format="%.2f"),
        "total": st.column_config.NumberColumn("Total", format="%.2f"),
        "category": st.column_config.SelectboxColumn("Category", options=cat_options),
        "material_item_key": st.column_config.SelectboxColumn("Material", options=mat_options),
        "notes": st.column_config.TextColumn("Notes"),
        "duplicate_note": st.column_config.TextColumn("Duplicates", disabled=True, width="small"),
        "subgroup": st.column_config.TextColumn("Subgroup", disabled=True, width="small"),
        "unit": st.column_config.TextColumn("Unit", disabled=True, width="small"),
    }
    editor_cfg = {k: v for k, v in mq_column_config.items() if k in vis_cols}

    edited_vis = st.data_editor(
        df[vis_cols],
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key=editor_key,
        column_order=editor_order,
        column_config=editor_cfg,
    )
    if edited_vis is None or edited_vis.empty:
        edited_vis = df[vis_cols].copy()

    prev_rows = list(st.session_state[SESSION_ROWS])
    merged_recs: list[dict[str, Any]] = []
    ev = edited_vis.fillna("")
    for i, er in enumerate(ev.to_dict("records")):
        base = dict(prev_rows[i]) if i < len(prev_rows) else _material_quote_seed_row()
        base.update(er)
        merged_recs.append(base)

    for r in merged_recs:
        try:
            qv = float(r.get("quantity", 0) or 0)
            uc = float(r.get("unit_cost", 0) or 0)
            r["total"] = round(qv * uc, 2)
        except (TypeError, ValueError):
            r["total"] = 0.0
        if not str(r.get("row_id") or "").strip():
            r["row_id"] = str(uuid.uuid4())
        r.setdefault("source_file", "")
        r.setdefault("vendor", "")
        r.setdefault("quote_number", "")
        r.setdefault("subgroup", "")
        r.setdefault("unit", "EA")
        r.setdefault("vendor_item_number", "")
        r.setdefault("material_item_key", "")
        r.setdefault("category", "")
        r.setdefault("notes", "")
        r.setdefault("include", True)
    _mark_duplicate_flags(merged_recs, inv_dup_keys)
    st.session_state[SESSION_ROWS] = merged_recs
    df2 = pd.DataFrame(merged_recs)

    save_quote_only = st.checkbox("Save quote record only (no new inventory lines)", value=False)
    import_to_inventory = st.checkbox(
        "Import included lines into Inventory (Materials)",
        value=True,
        key="mq_import_to_inventory",
    )
    save_source_file = st.checkbox("Upload original source files to storage when importing", value=True)
    allow_duplicates = st.checkbox(
        "Import lines even when marked as duplicates (otherwise those rows are skipped)",
        value=False,
        key="mq_allow_duplicates",
    )

    b1, b2 = st.columns(2)
    with b1:
        run_import_selected = st.button("Import Selected", use_container_width=True, help="Only rows with Include checked.")
    with b2:
        run_import_all = st.button("Import All", use_container_width=True, help="Import every row in the table (ignores Include).")

    def _do_import(*, all_rows: bool) -> None:
        markup = float(st.session_state.get("mq_markup_pct", DEFAULT_MARKUP_PCT * 100.0) or 0.0) / 100.0
        working = list(st.session_state[SESSION_ROWS])
        if all_rows:
            targets = list(working)
        else:
            targets = [r for r in working if bool(r.get("include", False))]
        if not targets:
            st.error("No rows to import." if all_rows else "No lines with Include checked.")
            return
        if not allow_duplicates:
            targets = [r for r in targets if not str(r.get("duplicate_note", "") or "").strip()]
        if not targets:
            st.error('No lines to import after skipping duplicates. Enable "Import lines even when marked as duplicates" or fix rows.')
            st.stop()
        for r in targets:
            vn = str(r.get("vendor", "") or "").strip()
            qn = str(r.get("quote_number", "") or "").strip()
            if not vn and not qn:
                st.error("Each imported line needs Vendor and/or Quote # (defaults come from the source file header).")
                st.stop()
                return

        by_file: dict[str, list[dict]] = {}
        for r in targets:
            sf = str(r.get("source_file") or "").strip() or "_unknown"
            by_file.setdefault(sf, []).append(r)

        imported_inv = 0
        linked_inv = 0
        storage_by_file: dict[str, str] = {}

        for source_name, file_rows in by_file.items():
            meta_bytes = None
            for qit in st.session_state[SESSION_QUEUE]:
                if qit["name"] == source_name:
                    meta_bytes = qit["bytes"]
                    break
            storage_path = ""
            if save_source_file and meta_bytes:
                try:
                    storage_path = _storage_name(source_name)
                    upload_bytes(storage_path, meta_bytes, content_type="application/octet-stream")
                    storage_by_file[source_name] = storage_path
                except Exception as exc:
                    st.warning(f"Could not store {source_name}: {exc}")

            first = file_rows[0]
            quote_payload = {
                "vendor_name": str(first.get("vendor", "") or "").strip(),
                "quote_number": str(first.get("quote_number", "") or "").strip(),
                "quote_date": None,
                "quote_total": float(sum(float(x.get("total", 0) or 0) for x in file_rows)),
                "shipping_total": 0.0,
                "tax_total": 0.0,
                "notes": "",
                "source_file_name": source_name,
                "source_file_path": storage_by_file.get(source_name, ""),
                "source_kind": "batch_import",
                "ai_confidence": 0.0,
                "created_by": current_profile().get("id"),
            }
            quote_row = insert_row_admin("material_quotes", quote_payload)
            qid = quote_row.get("id")
            line_number = 1
            for row in file_rows:
                qty = float(row.get("quantity", 0) or 0)
                uc = float(row.get("unit_cost", 0) or 0)
                ext = float(row.get("total", qty * uc) or 0)
                insert_row_admin(
                    "material_quote_items",
                    {
                        "material_quote_id": qid,
                        "line_number": line_number,
                        "vendor_item_number": str(row.get("vendor_item_number", "")).strip(),
                        "item_description": str(row.get("item_description", "")).strip(),
                        "category": str(row.get("category", "")).strip(),
                        "subgroup": str(row.get("subgroup", "")).strip(),
                        "unit": str(row.get("unit", "EA") or "EA").strip() or "EA",
                        "quantity": qty,
                        "unit_cost": uc,
                        "extended_cost": ext,
                        "unit_sell": compute_sell_price(uc, markup),
                        "source_page": "",
                        "notes": str(row.get("notes", "")).strip(),
                    },
                )
                line_number += 1

            if import_to_inventory and not save_quote_only:
                mat_local = list(materials)
                for row in file_rows:
                    description = str(row.get("item_description", "") or "").strip()
                    if not description:
                        continue
                    vin = str(row.get("vendor_item_number", "") or "").strip()
                    pick_key = str(row.get("material_item_key", "") or "").strip()
                    m_pick = next((m for m in mat_local if str(m.get("item_key") or "").strip() == pick_key), None)
                    m_match, _s = find_best_material_match(description, vin, mat_local)

                    use_existing = bool(pick_key and m_pick is not None)
                    if not use_existing and m_match is not None and pick_key == str(m_match.get("item_key") or "").strip():
                        use_existing = True

                    if use_existing and (m_pick is not None or m_match is not None):
                        linked_inv += 1
                        continue

                    base_item_key = clean_item_key(description)
                    final_item_key = make_unique_item_key(base_item_key, mat_local)
                    vend = str(row.get("vendor", "") or "").strip()
                    new_row = _insert_inventory_from_quote_line(
                        description=description,
                        subgroup=str(row.get("subgroup", "") or "").strip(),
                        unit=str(row.get("unit", "EA") or "EA").strip() or "EA",
                        unit_cost=float(row.get("unit_cost", 0) or 0),
                        final_item_key=final_item_key,
                        vendor_item_number=vin,
                        vendor_name=vend,
                    )
                    mat_local.append(new_row)
                    materials.append(new_row)
                    imported_inv += 1

        imported_ids = {str(r.get("row_id")) for r in targets}
        st.session_state[SESSION_ROWS] = [r for r in working if str(r.get("row_id")) not in imported_ids]
        st.session_state[SESSION_IMPORTED] = int(st.session_state.get(SESSION_IMPORTED, 0)) + imported_inv + linked_inv
        st.success(
            f"Import complete. New inventory: {imported_inv}; linked to existing catalog rows: {linked_inv}. "
            f"Quote rows saved per source file."
        )
        if return_to_materials:
            st.session_state.pop("materials_quote_import_mode", None)
        st.rerun()

    if run_import_selected:
        _do_import(all_rows=False)
    if run_import_all:
        _do_import(all_rows=True)

    sel = df2[df2["include"] == True]  # noqa: E712
    try:
        sel_total = float(sel["total"].astype(float).sum())
    except Exception:
        sel_total = 0.0
    n_inc = int(len(sel))
    footer = (
        f"<div class='mq-footer'><span><b>Checked lines:</b> {n_inc}</span>"
        f"<span><b>Checked total:</b> ${sel_total:,.2f}</span>"
        f"<span><b>Imported (session):</b> {int(st.session_state.get(SESSION_IMPORTED, 0))}</span>"
        f"<span><b>Rows in table:</b> {len(df2)}</span></div>"
    )
    st.markdown(footer, unsafe_allow_html=True)


def render() -> None:
    render_page_header("Material Quote Import", "Import vendor quotes into materials.")
    st.caption("Batch import vendor quotes (PDF / images). CSV and Excel are not supported in this uploader.")

    if current_role() not in {"admin", "pm"}:
        st.info("Only admin or pm users can use material quote import.")
        return

    render_material_quote_import_form(return_to_materials=False)
