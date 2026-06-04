# Known Data Bugs

**Source:** Read-only audit in [`CURRENT_APP_FLOW.md`](CURRENT_APP_FLOW.md) and code verification (2026-05-30).  
**Scope:** Data links, persistence, session state, status vocabulary, and cross-module handoffs.  
**Out of scope for this list:** Layout, CSS, UI component refactors, export-button UX (unless data never reaches DB).

Each item has an **ID** for tracking in [`FIX_ORDER.md`](FIX_ORDER.md) and [`DATA_FLOW_REPAIR_PLAN.md`](DATA_FLOW_REPAIR_PLAN.md).

**Status legend:** `open` = not started | `planned` = scheduled in fix order | `fixed` = resolved (update when code changes)

---

## Broken Database Links

| ID | Status | Module(s) | Issue | Primary code / tables |
|----|--------|-----------|-------|------------------------|
| DL-001 | open | Dashboard | Dollar KPIs and most charts use demo helpers; only some counts query Supabase. Dashboard is not a reliable link into live financial/ops data. | `app/pages/dashboard.py`, `_core/_data` demo loaders |
| DL-002 | open | Reports | All report sections use `demo_report_*`; CSV exports are sample rows, not DB-backed. | `app/pages/reports.py` |
| DL-003 | open | Employee Documents | Upload shows “Document uploaded (demo)”; `persist_employee_document()` not wired on main save path. Files never reach `employee_documents`. | `app/pages/employee_documents.py` |
| DL-004 | open | Job Costing | Labor tab is read-only from `time_entries`; no data path to correct missing labor if crew/timekeeping sync failed. | `app/pages/job_costing.py`, `time_entries` |
| DL-005 | open | Weekly Timesheets | Builder reads timekeeping hours; if day/allocation saves were not persisted, generated lines link to stale or empty hour data. | `weekly_timesheet_service`, `timekeeping` session |

---

## Demo / Non-Persistent Modules

| ID | Status | Module(s) | Issue | Primary code / tables |
|----|--------|-----------|-------|------------------------|
| NP-001 | open | Dashboard | Hybrid demo/live: counts may be real while dollar metrics and charts are hardcoded demo. | `dashboard.py` |
| NP-002 | open | Reports | Entire module is demo-backed; no Supabase queries in page render. | `reports.py` |
| NP-003 | open | Admin / Settings | “Save settings” writes session only; caption references future `company_settings` table. | `app/pages/admin.py` |
| NP-004 | open | Tasks | `demo-*` task IDs persist to `ips_task_local_overrides` in session only; never linked to `todos`. | `app/pages/tasks.py`, `_LOCAL_OVERRIDES_KEY` |
| NP-005 | open | Multiple | `is_demo_id()` rows skip Supabase persist/calculate on Estimates, Jobs, Assets, and related flows. UI appears live but is not in DB. | `app/pages/_core/_crud.py`, module pages |

---

## Broken Cross-Page Handoffs

| ID | Status | From → To | Issue | Primary code / session keys |
|----|--------|-----------|-------|----------------------------|
| XP-001 | open | Jobs → Job Costing | `jc_focus_job_id` set in `job_database_job_tasks.py`, not main `jobs.py`. Primary Jobs UI does not pass job context to Job Costing. | `jc_focus_job_id` |
| XP-002 | open | Estimates → Estimate Materials | Phase2 uses `app/pages/estimates.py`, which has no navigation to `estimate_materials`. Link exists only in `modules/estimates.py` (not router entry). | `ACTIVE_ESTIMATE_KEY`, `SESSION_NAV_KEY` |
| XP-003 | open | Coupling Inspection | Direct nav without launcher leaves `job_id` / `equipment_id` empty; page warns and cannot load inspection context. | `coupling_insp_*`, `coupling_inspection_launcher` |
| XP-004 | open | Timekeeping → Weekly Timesheets | Nav sets `ips_nav_page` → `weekly_timesheets`; prefill uses `wjt_prefill_job_id` pop. Broken if job/week context not set before navigate. | `wjt_prefill_job_id`, `ips_nav_page` |
| XP-005 | open | Field scan nav | `scan_inventory` / `scan_asset` use session flags, not `BUILT_MODULES` slug; permission and module shell differ from standard pages. | `_ips_inventory_scan_page`, `_ips_asset_scan_page`, `main.py` |

---

## Split Persistence Paths

| ID | Status | Area | Issue | Primary code / tables |
|----|--------|------|-------|------------------------|
| SP-001 | open | Inventory scan | Many paths call `update_rows_admin` on `inventory_items` / `assets`; only some use `record_inventory_transaction()`. Stock history and audit trail inconsistent. | `app/pages/inventory_scan.py`, `inventory_service` |
| SP-002 | open | Pricing Guide | If `pricing_guide_items` fetch fails, catalog falls back to `estimate_materials`. Estimates and inventory links may target wrong table. | `pricing_guide_service.py` |
| SP-003 | open | Lookups vs constants | Admin persists to `ips_lookup_*`, but pages fall back to `utils/constants` when lookups missing—dual source of truth. | `admin.py`, `lookup_service`, constants |
| SP-004 | open | Documents | `documents_hub` (Documents page) vs `employee_documents` (HR module)—overlapping purpose, no sync or single link model. | `documents.py`, `employee_documents.py` |
| SP-005 | open | Estimate Materials | Export, Edit Estimate, Add from Inventory, Add Custom Item buttons not wired to persist/load services—no data round-trip. | `estimate_materials.py` |

---

## Status Vocabulary Drift

| ID | Status | Module(s) | Issue | Notes |
|----|--------|-----------|-------|-------|
| SV-001 | open | Estimates | List `view_filter` hardcoded to `"Active Estimates"` in `render()`. Approved/Awarded/Rejected hidden regardless of DB. | `estimates.py` ~1318 |
| SV-002 | open | Tasks | UI Open/Closed; `status_to_db` writes `Open` / `Complete`; constants include In Progress, Done, Cancelled. | `task_display_helpers.py`, `constants.TASK_STATUSES` |
| SV-003 | open | Tasks | `normalize_task_status`: non-closed aliases (e.g. In Progress, Blocked) treated as **Open**. Closed views and counts wrong. | `task_display_helpers.py` |
| SV-004 | open | Assets | Page `_normalize_asset_status` (Available, In Service, …) vs `ASSET_STATUSES` (Active, Maintenance, Disposed). Filters and cross-module links disagree. | `assets.py`, `constants.py` |
| SV-005 | open | Jobs | Jobs normalizer (Draft, Planning, Awarded, …) vs `JOB_STATUSES` (Planning, Active, Completed, …). | `jobs.py`, `constants.py` |
| SV-006 | open | Customers | Open job/estimate counts use `_CLOSED_JOB_STATUSES` / `_CLOSED_EST_STATUSES` that do not match Jobs/Estimates list filter rules. | `customers.py` |

---

## Session State Bugs

| ID | Status | Module(s) | Issue | Session keys / behavior |
|----|--------|-----------|-------|-------------------------|
| SS-001 | open | Global nav | `on_nav_change` → `clear_all_module_selections()` clears all `ips_sel_*` and `ips_tab_*` on slug change. Cross-module selection/context lost. | `phase2.py`, `_session.py` |
| SS-002 | open | Estimate Materials | If `ACTIVE_ESTIMATE_KEY` empty, page defaults to first estimate in dropdown—wrong estimate context. | `ips_active_estimate_id` |
| SS-003 | open | Field mode | Toggling `ips_field_mode` resets nav to `field_dashboard`; prior office slug not preserved. | `ips_field_mode`, sidebar |
| SS-004 | open | Timekeeping | Allocation `by_date` in session (`_alloc_state_key`) until explicit save; rerun/nav before save shows unsaved allocation as if current. | `_alloc_state_key`, `timekeeping.py` |
| SS-005 | open | Coupling Inspection | Unsaved work in `coupling_insp_draft` until `save_coupling_inspection`; refresh loses draft if not saved. | `coupling_insp_draft` |
| SS-006 | open | Field vs office Timekeeping | Field users get filtered summaries; same employee/week may differ from office list—appears inconsistent. | `_filter_summaries_for_field_user` |

---

## Cache / Stale Data Bugs

| ID | Status | Module(s) | Issue | Notes |
|----|--------|-----------|-------|-------|
| CD-001 | open | Assets | Equipment and Small Tools share `SELECTED_ASSET_KEY`, `SHOW_ASSET_MODAL_KEY`, `_ASSETS_CACHE_KEY`. Tab switch or uncheck can point modal at different asset than row. | `assets.py` |
| CD-002 | open | Assets | Kit item row ID (`kititem_*`) vs modal `SELECTED_ASSET_KEY` (parent asset ID)—selection state and visible row can diverge. | `_small_tool_modal_asset_id` |
| CD-003 | open | Assets / Equipment list | `build_modal_cache(filtered)` uses full filtered set; table shows `page_rows`—IDs should be in cache, but pagination + shared keys increase stale-selection risk. | `_ASSETS_CACHE_KEY` |
| CD-004 | open | Modal caches | Module modal caches (`build_modal_cache`) not invalidated on all persist paths—risk of stale record in detail modal after edit elsewhere. | `record_modal.py`, per-page caches |

---

## Orphaned Modules

| ID | Status | Module | Issue | Notes |
|----|--------|--------|-------|-------|
| OR-001 | open | `estimate_materials` | In `BUILT_MODULES` but not in office `NAV_PAGES`. No link from active `estimates.py`. Reachable only via slug/deeplink or dead `modules/estimates.py` path. | `phase2.py`, `constants.NAV_PAGES` |
| OR-002 | open | `employee_certifications` | Not in office sidebar; in field nav and permissions. Office users may not discover route. | `FIELD_NAV_PAGES` |
| OR-003 | open | `employee_documents` | Not in office sidebar; separate from Documents hub with duplicate purpose. | Nav + DL-003 |

---

## Production Data Pollution Risks

| ID | Status | Module(s) | Issue | Primary code |
|----|--------|-----------|-------|--------------|
| PP-001 | open | Users (Employees) | `ensure_core_employee_seed()` runs on page load; can insert seed employees into DB once per environment. | `employee_seed_service.py`, `employees.py` |
| PP-002 | open | Tasks / Estimates / Jobs | Demo IDs and session overrides can be mistaken for production records in UI lists mixed with real Supabase rows. | `is_demo_id`, demo loaders in `_data.py` |
| PP-003 | open | Inventory scan | Direct `update_rows_admin` quantity changes without transaction rows—harder to audit corrections in production. | `inventory_scan.py` |

---

## Modules With the Most Broken Links (summary)

| Priority | Module | Bug IDs (sample) |
|----------|--------|------------------|
| Critical | Reports | DL-002, NP-002 |
| Critical | Employee Documents | DL-003, OR-003 |
| Critical | Inventory scan | SP-001, PP-003 |
| High | Estimates / Estimate Materials | SV-001, XP-002, OR-001, SP-005 |
| High | Jobs / Job Costing | XP-001, DL-004 |
| High | Timekeeping / Weekly Timesheets | SS-004, DL-005, XP-004 |
| High | Tasks | NP-004, SV-002, SV-003 |
| Medium | Dashboard | DL-001, NP-001 |
| Medium | Pricing Guide | SP-002 |
| Medium | Customers | SV-006 |
| Medium | Assets | SV-004, CD-001, CD-002 |
| Medium | Admin / Settings | NP-003, SP-003 |
| Medium | Coupling Inspection | XP-003, SS-005 |

---

## Related documentation

- Current behavior (as-is): [`CURRENT_APP_FLOW.md`](CURRENT_APP_FLOW.md)
- Fix sequence: [`FIX_ORDER.md`](FIX_ORDER.md)
- Repair strategy and acceptance criteria: [`DATA_FLOW_REPAIR_PLAN.md`](DATA_FLOW_REPAIR_PLAN.md)

*Last updated: 2026-05-30. Update **Status** column when fixes land.*
