from __future__ import annotations

import re
from datetime import datetime

import pandas as pd
import streamlit as st

try:
    from auth import current_profile, current_role
    from branding import render_header
    from db import fetch_table, insert_row_admin, upload_bytes
    from services.material_quote_import import DEFAULT_MARKUP_PCT, compute_sell_price, extract_material_quote
except ImportError:
    from app.auth import current_profile, current_role  # type: ignore
    from app.branding import render_header  # type: ignore
    from app.db import fetch_table, insert_row_admin, upload_bytes  # type: ignore
    from app.services.material_quote_import import DEFAULT_MARKUP_PCT, compute_sell_price, extract_material_quote  # type: ignore


def next_inventory_id(rows) -> str:
    nums = []
    for row in rows:
        inv = str(row.get("inventory_id", "")).strip().upper()
        if inv.startswith("INV-"):
            try:
                nums.append(int(inv.replace("INV-", "")))
            except Exception:
                pass
    next_num = max(nums) + 1 if nums else 1
    return f"INV-{next_num:03d}"


def clean_item_key(text: str) -> str:
    text = str(text).strip().upper()
    text = re.sub(r"[^A-Z0-9]+", "_", text)
    return text.strip("_")


def make_unique_item_key(base_key: str, rows) -> str:
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
    """
    Return the best catalog row and a score in [0, 1].
    Prefer vendor item # exact match, else token overlap + substring on description.
    """
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


def _format_material_suggestion(row: dict | None) -> str:
    if not row:
        return "—"
    desc = str(row.get("description", "") or "").strip()
    if len(desc) > 72:
        desc = desc[:69] + "…"
    inv = str(row.get("inventory_id", "") or "").strip()
    ik = str(row.get("item_key", "") or "").strip()
    return f"{inv} | {ik} | {desc}" if desc else f"{inv} | {ik}"


def render_material_quote_import_form(*, return_to_materials: bool = False) -> None:
    """
    Vendor quote upload, AI extraction, editable grid, save to material_quotes /
    material_quote_items / materials_catalog. Caller handles page chrome and access control.
    """
    materials = fetch_table("materials_catalog", limit=5000, order_by="item_key")

    if "material_quote_result" not in st.session_state:
        st.session_state["material_quote_result"] = None
    if "material_quote_file_meta" not in st.session_state:
        st.session_state["material_quote_file_meta"] = None

    uploaded = st.file_uploader(
        "Upload vendor quote",
        type=["pdf", "jpg", "jpeg", "png", "webp", "csv", "xlsx", "xls"],
        accept_multiple_files=False,
    )

    if uploaded is not None:
        file_bytes = uploaded.getvalue()
        ext = uploaded.name.rsplit(".", 1)[-1].lower() if "." in uploaded.name else ""

        st.write(f"**File:** {uploaded.name}")
        st.write(f"**Type:** {ext.upper()}")

        if ext in {"jpg", "jpeg", "png", "webp"}:
            st.image(file_bytes, caption=uploaded.name, use_container_width=True)

        if st.button("Analyze Quote", use_container_width=True):
            with st.spinner("Analyzing quote..."):
                try:
                    result = extract_material_quote(file_bytes, uploaded.name)
                    st.session_state["material_quote_result"] = result
                    st.session_state["material_quote_file_meta"] = {
                        "name": uploaded.name,
                        "bytes": file_bytes,
                        "ext": ext,
                    }
                    st.success("Quote analyzed.")
                except Exception as exc:
                    st.error(str(exc))

    result = st.session_state.get("material_quote_result")
    meta = st.session_state.get("material_quote_file_meta")

    if not result:
        return

    st.markdown("---")
    st.subheader("Review Quote")

    top1, top2, top3, top4 = st.columns(4, gap="small")
    top1.metric("Confidence", f"{float(result.get('confidence', 0) or 0) * 100:.0f}%")
    top2.metric("Items Found", len(result.get("items", [])))
    top3.metric("Quote Total", f"${float(result.get('quote_total', 0) or 0):,.2f}")
    top4.metric("Source", str(result.get("source_kind", "")).replace("_", " ").title())

    flags = result.get("review_flags", [])
    if flags:
        st.warning("Review flags: " + ", ".join(flags))

    col1, col2, col3, col4 = st.columns(4, gap="small")
    vendor_name = col1.text_input("Vendor Name", value=result.get("vendor_name", ""))
    quote_number = col2.text_input("Quote Number", value=result.get("quote_number", ""))
    quote_date = col3.text_input("Quote Date", value=result.get("quote_date", ""))
    default_markup = col4.number_input("Default Markup %", min_value=0.0, value=float(DEFAULT_MARKUP_PCT * 100), step=1.0) / 100.0

    fin1, fin2, fin3 = st.columns(3, gap="small")
    quote_total = fin1.number_input("Quote Total", min_value=0.0, value=float(result.get("quote_total", 0) or 0), step=1.0)
    shipping_total = fin2.number_input("Shipping", min_value=0.0, value=float(result.get("shipping_total", 0) or 0), step=1.0)
    tax_total = fin3.number_input("Tax", min_value=0.0, value=float(result.get("tax_total", 0) or 0), step=1.0)

    quote_notes = st.text_area("Quote Notes", value=result.get("notes", ""), height=72)

    suggest_threshold = 0.35

    rows = []
    for item in result.get("items", []):
        unit_cost = float(item.get("unit_cost", 0) or 0)
        quantity = float(item.get("quantity", 0) or 0)
        extended_cost = float(item.get("extended_cost", quantity * unit_cost) or 0)
        desc = item.get("item_description", "")
        vin = item.get("vendor_item_number", "")
        match_row, match_score = find_best_material_match(desc, vin, materials)

        rows.append(
            {
                "import_item": True,
                "item_description": desc,
                "vendor_item_number": vin,
                "category": item.get("category", ""),
                "subgroup": item.get("subgroup", ""),
                "unit": item.get("unit", "EA"),
                "quantity": quantity,
                "unit_cost": unit_cost,
                "extended_cost": extended_cost,
                "unit_sell": compute_sell_price(unit_cost, default_markup),
                "suggested_match": _format_material_suggestion(match_row),
                "use_existing": bool(match_row is not None and match_score >= suggest_threshold),
                "source_page": item.get("source_page", ""),
                "notes": item.get("notes", ""),
            }
        )

    if not rows:
        rows = [{
            "import_item": True,
            "item_description": "",
            "vendor_item_number": "",
            "category": "",
            "subgroup": "",
            "unit": "EA",
            "quantity": 0.0,
            "unit_cost": 0.0,
            "extended_cost": 0.0,
            "unit_sell": 0.0,
            "suggested_match": "—",
            "use_existing": False,
            "source_page": "",
            "notes": "",
        }]

    st.caption(
        "Suggested catalog match uses vendor # and description similarity. "
        "Check **Use existing** to skip creating a duplicate SKU when the match is correct."
    )

    editor_key = "material_quote_editor_embed" if return_to_materials else "material_quote_editor"
    df = pd.DataFrame(rows)
    edited = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key=editor_key,
        column_config={
            "suggested_match": st.column_config.TextColumn(
                "Suggested catalog match",
                help="Existing materials_catalog row that looks like this line.",
                disabled=True,
                width="large",
            ),
            "use_existing": st.column_config.CheckboxColumn(
                "Use existing",
                help="When checked, this line will not create a new catalog item if a match is found.",
            ),
        },
    )

    save_quote_only = st.checkbox("Save quote record only", value=False)
    import_to_materials = st.checkbox("Import selected items into Materials Catalog", value=True)
    save_source_file = st.checkbox("Upload original file to storage", value=True)

    if st.button("Save Quote Import", use_container_width=True):
        cleaned_rows = edited.fillna("").to_dict("records")
        selected_rows = [row for row in cleaned_rows if bool(row.get("import_item", False))]

        if not vendor_name.strip() and not quote_number.strip():
            st.error("Enter at least Vendor Name or Quote Number.")
            return

        storage_path = ""
        if save_source_file and meta:
            try:
                storage_path = _storage_name(meta["name"])
                upload_bytes(storage_path, meta["bytes"], content_type="application/octet-stream")
            except Exception as exc:
                st.warning(f"Could not upload source file: {exc}")
                storage_path = ""

        quote_payload = {
            "vendor_name": vendor_name.strip(),
            "quote_number": quote_number.strip(),
            "quote_date": quote_date.strip() or None,
            "quote_total": float(quote_total or 0),
            "shipping_total": float(shipping_total or 0),
            "tax_total": float(tax_total or 0),
            "notes": quote_notes.strip(),
            "source_file_name": meta.get("name", "") if meta else "",
            "source_file_path": storage_path,
            "source_kind": result.get("source_kind", ""),
            "ai_confidence": float(result.get("confidence", 0) or 0),
            "created_by": current_profile().get("id"),
        }
        quote_row = insert_row_admin("material_quotes", quote_payload)

        line_number = 1
        for row in cleaned_rows:
            quantity = float(row.get("quantity", 0) or 0)
            unit_cost = float(row.get("unit_cost", 0) or 0)
            extended_cost = float(row.get("extended_cost", quantity * unit_cost) or 0)

            insert_row_admin(
                "material_quote_items",
                {
                    "material_quote_id": quote_row.get("id"),
                    "line_number": line_number,
                    "vendor_item_number": str(row.get("vendor_item_number", "")).strip(),
                    "item_description": str(row.get("item_description", "")).strip(),
                    "category": str(row.get("category", "")).strip(),
                    "subgroup": str(row.get("subgroup", "")).strip(),
                    "unit": str(row.get("unit", "")).strip() or "EA",
                    "quantity": quantity,
                    "unit_cost": unit_cost,
                    "extended_cost": extended_cost,
                    "unit_sell": float(row.get("unit_sell", 0) or 0),
                    "source_page": str(row.get("source_page", "")).strip(),
                    "notes": str(row.get("notes", "")).strip(),
                },
            )
            line_number += 1

        imported_count = 0
        linked_existing_count = 0
        if import_to_materials and not save_quote_only:
            for row in selected_rows:
                description = str(row.get("item_description", "")).strip()
                if not description:
                    continue

                use_existing = bool(row.get("use_existing", False))
                vin = str(row.get("vendor_item_number", "")).strip()
                m, _score = find_best_material_match(description, vin, materials)

                if use_existing and m is not None:
                    linked_existing_count += 1
                    continue

                base_item_key = clean_item_key(description)
                final_item_key = make_unique_item_key(base_item_key, materials)
                final_inventory_id = next_inventory_id(materials)

                material_payload = {
                    "inventory_id": final_inventory_id,
                    "item_key": final_item_key,
                    "description": description,
                    "category": str(row.get("category", "")).strip(),
                    "subgroup": str(row.get("subgroup", "")).strip(),
                    "unit": str(row.get("unit", "")).strip() or "EA",
                    "purchase_price": float(row.get("unit_cost", 0) or 0),
                    "sell_price": float(row.get("unit_sell", 0) or 0),
                    "vendor_item_number": str(row.get("vendor_item_number", "")).strip(),
                    "is_active": True,
                }
                insert_row_admin("materials_catalog", material_payload)
                materials.append(material_payload)
                imported_count += 1

        st.success(
            f"Material quote imported successfully. "
            f"Quote lines saved: {len(cleaned_rows)}. "
            f"Catalog: {imported_count} new, {linked_existing_count} linked to existing (no duplicate SKU)."
        )
        st.session_state["material_quote_result"] = None
        st.session_state["material_quote_file_meta"] = None
        if return_to_materials:
            st.session_state.pop("materials_quote_import_mode", None)
        st.rerun()


def render() -> None:
    render_header("Material Quote Import")
    st.caption("Import vendor quotes from images, PDFs, CSV, or Excel.")

    if current_role() not in {"admin", "pm"}:
        st.info("Only admin or pm users can use material quote import.")
        return

    render_material_quote_import_form(return_to_materials=False)
