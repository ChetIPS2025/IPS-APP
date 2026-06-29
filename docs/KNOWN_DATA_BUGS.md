# Known Data Bugs

**Source:** Audit in [`CURRENT_APP_FLOW.md`](CURRENT_APP_FLOW.md), plus code verification through **2026-05-30**.  
**Scope:** Data links, persistence, session state, status vocabulary, and cross-module handoffs.  
**Out of scope:** Layout/CSS refactors, export-button UX (unless data never reaches DB).

Each item has an **ID** for tracking in [`FIX_ORDER.md`](FIX_ORDER.md) and [`DATA_FLOW_REPAIR_PLAN.md`](DATA_FLOW_REPAIR_PLAN.md).

**Status legend:** `open` = not started | `planned` = scheduled | `partial` = live path shipped; sample fallback or minor gap remains | `fixed` = resolved

---

## Recently resolved (2026-05 – 2026-06)

| ID | Resolution |
|----|------------|
| DL-001, NP-001 | Dashboard KPIs and charts read Supabase when rows exist; empty/missing data shows **Sample data** badges and a KPI banner. |
| DL-002, NP-002 | Reports query `reports_service` live helpers; sections show **Live data** / **Sample data** badges. |
| DL-003 | Employee Documents upload/edit persist via `employee_documents_service` + Storage (`employee-documents` bucket). |
| XP-001 – XP-005 | Cross-module handoffs: Jobs→Costing, Estimates→Materials, Coupling launcher guard, Timekeeping→Timesheets, scan embed routes. |
| SP-001, PP-003 | Shop/job inventory scans route through `record_shop_inventory_consumption` / `record_inventory_transaction`. |
| SP-005 | Estimate Materials: CSV export, Edit Estimate, Add from Inventory, Add Custom Item wired. |
| Field loop | Scans, labor rollup, per-job email settings feed job costing (see commits on `main` May–Jun 2026). |

---

## Broken Database Links

| ID | Status | Module(s) | Issue | Primary code / tables |
|----|--------|-----------|-------|------------------------|
| DL-001 | fixed | Dashboard | ~~Demo KPIs/charts~~ Now live from estimates/jobs/inventory when connected; sample fallbacks are labeled. | `dashboard.py`, `dashboard_metrics_service.py`, `_core/_data.py` |
| DL-002 | fixed | Reports | ~~Demo-only reports~~ Live queries via `reports_service`; sample rows only when live fetch empty. | `reports.py`, `reports_service.py` |
| DL-003 | fixed | Employee Documents | ~~Demo upload path~~ Wired to `persist_employee_document()` + Storage. Requires `employee-documents` bucket. | `employee_documents.py`, `employee_documents_service.py` |
| DL-004 | open | Job Costing | Labor tab is read-only from `time_entries`; no admin path to correct missing labor if crew/timekeeping sync failed. | `job_costing.py`, `time_entries` |
| DL-005 | open | Weekly Timesheets | Builder reads timekeeping hours; unsaved day/allocation data yields stale generated lines. | `weekly_timesheet_service`, `timekeeping` session |

---

## Demo / Non-Persistent Modules

| ID | Status | Module(s) | Issue | Primary code / tables |
|----|--------|-----------|-------|------------------------|
| NP-001 | fixed | Dashboard | ~~Unlabeled demo/live mix~~ Live when Supabase has data; **Sample data** badges on panels without rows. | `dashboard.py` |
| NP-002 | fixed | Reports | ~~Entire module demo~~ Live-backed with labeled sample fallback. | `reports.py` |
| NP-003 | open | Admin / Settings | “Save settings” writes session only; caption references future `company_settings` table. | `admin.py` |
| NP-004 | open | Tasks | `demo-*` task IDs persist to session overrides only; never linked to `todos`. | `tasks.py`, `_LOCAL_OVERRIDES_KEY` |
| NP-005 | open | Multiple | `is_demo_id()` rows skip Supabase persist on Estimates, Jobs, Assets, etc. UI can look live but is not in DB. | `_crud.py`, module pages |

---

## Broken Cross-Page Handoffs

| ID | Status | From → To | Issue | Primary code / session keys |
|----|--------|-----------|-------|----------------------------|
| XP-001 | fixed | Jobs → Job Costing | `open_jobs_job_costing` / `jc_focus_job_id` set from Jobs detail. | `navigation.py`, `jobs.py` |
| XP-002 | fixed | Estimates → Estimate Materials | `navigate_to_estimate_materials()` sets `ACTIVE_ESTIMATE_KEY`. | `estimates.py`, `navigation.py` |
| XP-003 | partial | Coupling Inspection | Launcher context required; direct nav still warns—by design, document keys for support. | `coupling_inspection.py` |
| XP-004 | fixed | Timekeeping → Weekly Timesheets | `navigate_to_weekly_timesheet()` sets job/week prefill keys. | `navigation.py`, `timekeeping.py` |
| XP-005 | fixed | Field scan nav | Scan routes embedded in module shell via `INVENTORY_SCAN_EMBED_KEY` / `ASSET_SCAN_EMBED_KEY`. | `navigation.py`, `inventory.py`, `assets.py` |

---

## Split Persistence Paths

| ID | Status | Area | Issue | Primary code / tables |
|----|--------|------|-------|------------------------|
| SP-001 | fixed | Inventory scan | Primary shop/job consumption paths use `record_inventory_transaction()`. Audit any remaining direct qty updates in scan edge paths. | `inventory_scan.py`, `inventory_service.py` |
| SP-002 | open | Pricing Guide | If `pricing_guide_items` fetch fails, catalog falls back to `estimate_materials` silently in prod. | `pricing_guide_service.py` |
| SP-003 | open | Lookups vs constants | Admin persists to `ips_lookup_*`; pages fall back to `utils/constants` when lookups missing. | `admin.py`, `lookup_service` |
| SP-004 | open | Documents | `documents_hub` vs `employee_documents` overlap; no single link model documented for users. | `documents.py`, `employee_documents.py` |
| SP-005 | fixed | Estimate Materials | Export, Edit Estimate, Add from Inventory, Add Custom Item wired to persist/navigation. | `estimate_materials.py` |

---

## Status Vocabulary Drift

| ID | Status | Module(s) | Issue | Notes |
|----|--------|-----------|-------|-------|
| SV-001 | open | Estimates | List `view_filter` hardcoded to `"Active Estimates"`. Approved/Awarded/Rejected hidden regardless of DB. | `estimates.py` |
| SV-002 | open | Tasks | UI Open/Closed vs DB `Open`/`Complete` vs constants (In Progress, Done, Cancelled). | `task_display_helpers.py` |
| SV-003 | open | Tasks | `normalize_task_status` treats In Progress/Blocked as Open. | `task_display_helpers.py` |
| SV-004 | open | Assets | Page normalizer vs `ASSET_STATUSES` in constants disagree. | `assets.py`, `constants.py` |
| SV-005 | open | Jobs | Jobs normalizer vs `JOB_STATUSES` in constants disagree. | `jobs.py`, `constants.py` |
| SV-006 | open | Customers | Open job/estimate counts use closed-status sets that don't match Jobs/Estimates filters. | `customers.py` |

---

## Session State Bugs

| ID | Status | Module(s) | Issue | Session keys / behavior |
|----|--------|-----------|-------|-------------------------|
| SS-001 | open | Global nav | `on_nav_change` clears module selections; cross-module context can be lost. | `phase2.py`, `_session.py` |
| SS-002 | open | Estimate Materials | If `ACTIVE_ESTIMATE_KEY` empty, page defaults to first estimate in dropdown. | `ips_active_estimate_id` |
| SS-003 | open | Field mode | Toggling field mode resets nav to `field_dashboard`. | `ips_field_mode` |
| SS-004 | open | Timekeeping | Allocation draft in session until save; nav before save looks persisted. | `_alloc_state_key` |
| SS-005 | open | Coupling Inspection | Unsaved draft in `coupling_insp_draft` lost on refresh. | `coupling_insp_draft` |
| SS-006 | open | Field vs office Timekeeping | Field-filtered summaries can differ from office view for same week. | `_filter_summaries_for_field_user` |

---

## Cache / Stale Data Bugs

| ID | Status | Module(s) | Issue | Notes |
|----|--------|-----------|-------|-------|
| CD-001 | open | Assets | Equipment and Small Tools share selection/modal keys. | `assets.py` |
| CD-002 | open | Assets | Kit row ID vs parent asset modal key can diverge. | `_small_tool_modal_asset_id` |
| CD-003 | open | Assets | Pagination + shared modal cache stale-selection risk. | `_ASSETS_CACHE_KEY` |
| CD-004 | open | Modal caches | Modal caches not invalidated on all persist paths. | `record_modal.py` |

---

## Orphaned Modules

| ID | Status | Module | Issue | Notes |
|----|--------|--------|-------|-------|
| OR-001 | partial | `estimate_materials` | Handoff from Estimates works; still **not** in office `NAV_PAGES` sidebar. | `constants.NAV_PAGES`, `estimates.py` |
| OR-002 | open | `employee_certifications` | Not in office sidebar; in field nav only. | `FIELD_NAV_PAGES` |
| OR-003 | partial | `employee_documents` | Persist path fixed (DL-003); still not in office sidebar; overlaps Documents hub. | Nav + `employee_documents.py` |

---

## Production Data Pollution Risks

| ID | Status | Module(s) | Issue | Primary code |
|----|--------|-----------|-------|--------------|
| PP-001 | open | Users (Employees) | `ensure_core_employee_seed()` runs on page load; can insert seed employees. | `employee_seed_service.py` |
| PP-002 | open | Tasks / Estimates / Jobs | Demo IDs mixed with live rows in UI lists. | `is_demo_id`, `_data.py` |
| PP-003 | fixed | Inventory scan | Shop/job consumption records inventory transactions for audit trail. | `inventory_service.py` |

---

## Modules — remaining priority

| Priority | Module | Open bug IDs |
|----------|--------|--------------|
| High | Timekeeping / Weekly Timesheets | SS-004, DL-005 |
| High | Tasks | NP-004, SV-002, SV-003 |
| High | Job Costing | DL-004 |
| Medium | Estimates / Materials | SV-001, OR-001 (sidebar) |
| Medium | Pricing Guide | SP-002 |
| Medium | Customers | SV-006 |
| Medium | Assets | SV-004, CD-001–CD-003 |
| Medium | Admin / Settings | NP-003, SP-003 |
| Medium | Coupling Inspection | XP-003 (docs), SS-005 |
| Low | Session / nav polish | SS-001, SS-003, SS-006 |

---

## Related documentation

- Current behavior: [`CURRENT_APP_FLOW.md`](CURRENT_APP_FLOW.md)
- Fix sequence: [`FIX_ORDER.md`](FIX_ORDER.md)
- Strategy: [`DATA_FLOW_REPAIR_PLAN.md`](DATA_FLOW_REPAIR_PLAN.md)

*Last updated: 2026-06-28. Update **Status** when fixes land.*
