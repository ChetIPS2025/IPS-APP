# Fix Order — Data Flow Repair

**Purpose:** Ordered work sequence to make IPS Operations data flows reliable **before** any layout or CSS work.  
**Tracker:** Bug IDs defined in [`KNOWN_DATA_BUGS.md`](KNOWN_DATA_BUGS.md).  
**Strategy:** [`DATA_FLOW_REPAIR_PLAN.md`](DATA_FLOW_REPAIR_PLAN.md).

**Progress (Jun 2026):** Phases 1–2 and Phase 5 (catalog/settings SSOT) largely complete. Phase 3 status maps shipped. Next focus: session/cache (Phase 4), job costing chain (Phase 6).

**Rules for all phases:**
- No layout, CSS, or UI component refactors unless required to wire data (e.g. a button that must call an existing service).
- Prefer fixing services, session handoffs, and status normalization—not visual redesign.
- Each phase should be deployable without breaking unrelated modules.

---

## Phase 0 — Triage and guardrails (documentation + flags)

**Goal:** Stop new pollution and make demo vs live obvious in code paths.

| Order | Bug ID | Action | Owner hint |
|-------|--------|--------|------------|
| 0.1 | PP-001 | Gate `ensure_core_employee_seed()` behind env flag or explicit admin action; document seed behavior. | `employees.py`, `employee_seed_service` |
| 0.2 | NP-005 | Audit all `is_demo_id` branches; document which UI actions silently no-op. | `_crud.py`, estimates, jobs, assets |
| 0.3 | — | Add “data contract” comments on `record_inventory_transaction`, `ACTIVE_ESTIMATE_KEY`, `jc_focus_job_id` (code comment only when approved). | services / pages |

**Exit criteria:** No automatic seed on production without opt-in; demo ID behavior documented in KNOWN_DATA_BUGS.

---

## Phase 1 — Critical persistence (data never reaches DB)

**Goal:** User actions that imply “saved” actually persist to Supabase.

| Order | Bug ID | Action | Files (expected) |
|-------|--------|--------|------------------|
| 1.1 | DL-003 | Wire Employee Documents upload to `persist_employee_document()` + storage; remove demo success path. | `employee_documents.py`, document service |
| 1.2 | SP-001, PP-003 | Route all inventory scan stock changes through `record_inventory_transaction()`; deprecate direct `update_rows_admin` on quantity for movement flows. | `inventory_scan.py`, `inventory_service` |
| 1.3 | SP-005 | Wire Estimate Materials actions to existing estimate/material persist APIs (or hide buttons until wired). | `estimate_materials.py`, `estimates_service` |
| 1.4 | NP-004 | Either persist demo tasks to DB on first edit or block demo IDs from Create Task with clear message. | `tasks.py`, `tasks_service` |

**Exit criteria:** Upload doc, scan checkout, add material line, and create task (non-demo) all verifiable in Supabase.

---

## Phase 2 — Cross-page handoffs and orphaned routes

**Goal:** Navigation and session keys pass the correct record context between modules.

| Order | Bug ID | Action | Files (expected) |
|-------|--------|--------|------------------|
| 2.1 | XP-002, OR-001 | Add Estimates → Estimate Materials handoff in `estimates.py` (set `ACTIVE_ESTIMATE_KEY`, `set_nav_slug('estimate_materials')`); optional sidebar entry. | `estimates.py`, `navigation` (slug only, not layout) |
| 2.2 | XP-001 | Set `jc_focus_job_id` from Jobs detail modal / list action (mirror `job_database_job_tasks` behavior). | `jobs.py`, `job_costing.py` |
| 2.3 | XP-003 | Block or redirect Coupling Inspection nav unless launcher context present; document required session keys. | `coupling_inspection.py`, launcher |
| 2.4 | XP-004 | Standardize Timekeeping → Weekly Timesheets: set `wjt_prefill_job_id` + week when opening builder. | `timekeeping.py`, `weekly_timesheets.py` |
| 2.5 | SS-002 | Estimate Materials: require `ACTIVE_ESTIMATE_KEY` or explicit picker change before load—no silent first-row default. | `estimate_materials.py` |

**Exit criteria:** Manual test scripts in DATA_FLOW_REPAIR_PLAN § Acceptance pass for handoffs 2.1–2.4.

---

## Phase 3 — Status vocabulary and list filters (data visibility)

**Goal:** Lists, counts, and DB writes use one normalized status model per entity.

| Order | Bug ID | Action | Files (expected) |
|-------|--------|--------|------------------|
| 3.1 | SV-001 | Expose estimate view filter in UI or remove hardcode; align with `_apply_estimate_view_filter` options. | `estimates.py` |
| 3.2 | SV-002, SV-003 | Align task `status_to_db`, `normalize_task_status`, and DB values with `TASK_STATUSES` or document canonical map. | `task_display_helpers.py`, `tasks_service` |
| 3.3 | SV-004 | Single asset status canonical map: page normalizer ↔ DB ↔ constants. | `assets.py`, `constants.py` |
| 3.4 | SV-005, SV-006 | Align job closed/active rules across Jobs list, Customers counts, and constants. | `jobs.py`, `customers.py` |

**Exit criteria:** Same record shows consistent status on list, modal, and customer summary; filter “Active” matches count logic.

---

## Phase 4 — Session state and cache reliability

**Goal:** Context survives intentional navigation; modal selection matches records.

| Order | Bug ID | Action | Files (expected) |
|-------|--------|--------|------------------|
| 4.1 | SS-001 | Selective clear on nav: preserve `ACTIVE_ESTIMATE_KEY`, `ips_field_job_id`, job costing focus when appropriate. | `phase2.py`, `_session.py` |
| 4.2 | SS-004 | Persist allocation draft on row expand save or warn on nav if unsaved `by_date` dirty flag. | `timekeeping.py`, allocation persist |
| 4.3 | CD-001, CD-002 | Separate or namespaced selection keys for Equipment vs Small Tools; kit row opens parent with consistent checkbox state. | `assets.py` |
| 4.4 | CD-004 | Invalidate modal cache after persist in each module (pattern from `clear_*_cache` helpers). | `record_modal.py`, page modules |
| 4.5 | SS-005 | Optional: autosave coupling draft to session table or warn on leave. | `coupling_inspection.py` |

**Exit criteria:** Navigate Estimates → Materials → back without losing estimate id; timekeeping allocation save survives rerun.

---

## Phase 5 — Single source of truth for catalogs and settings

**Goal:** Remove split persistence paths that fork data.

| Order | Bug ID | Action | Files (expected) |
|-------|--------|--------|------------------|
| 5.1 | SP-002 | Migrate/fail loud on missing `pricing_guide_items`; remove silent `estimate_materials` fallback in production. | `pricing_guide_service.py` |
| 5.2 | SP-003 | Lookups: prefer `ips_lookup_*` with constants as seed only, not runtime fallback. | `lookup_service`, loaders |
| 5.3 | NP-003 | Persist application settings to `company_settings` (or remove Save until table exists). | `admin.py`, migration |
| 5.4 | SP-004 | Document link model: when to use `documents_hub` vs `employee_documents`; optional FK alignment. | docs + services |

**Exit criteria:** Pricing item saved in guide appears in estimate builder from same id; settings survive refresh.

---

## Phase 6 — Downstream job costing and timesheet chain

**Goal:** End-to-end office time → job cost → customer timesheet uses same hour data.

| Order | Bug ID | Action | Files (expected) |
|-------|--------|--------|------------------|
| 6.1 | SS-004, DL-005 | Ensure allocation + day hours persist before week submit; weekly builder reads same source as job costing. | `timekeeping` services |
| 6.2 | DL-004 | Document labor source; optional admin “refresh labor from time_entries” if sync gap found. | `job_costing.py` |
| 6.3 | — | Verify crew time approve → `time_entries` → timekeeping → weekly timesheet (integration test). | `field_crew_time`, services |

**Exit criteria:** Approve crew batch → see hours in Job Costing labor and Weekly Timesheet generate.

---

## Phase 7 — Demo-backed modules (replace or gate)

**Goal:** No module presents fiction as production data without explicit “Sample data” mode.

| Order | Bug ID | Action | Files (expected) |
|-------|--------|--------|------------------|
| 7.1 | DL-002, NP-002 | Reports: connect to real queries or gate module with “Demo reports only” banner for all roles. | `reports.py`, new report queries |
| 7.2 | DL-001, NP-001 | Dashboard: wire charts to same tables as Jobs/Estimates or label panels Demo. | `dashboard.py` |
| 7.3 | DL-003 | (if not done in 1.1) | — |

**Exit criteria:** Admin can trust Dashboard/Reports numbers or see explicit demo labeling.

---

## Deferred (explicitly not in data-flow fix order)

| Item | Reason |
|------|--------|
| Export CSV buttons (Jobs, Inventory, etc.) | UX/reporting; not blocking DB integrity |
| Layout / CSS / Streamlit columns | Out of scope per repair plan |
| Field duplicate pages (`field_day` vs standalone daily reports) | UX consolidation, not data link |
| Inventory Action vs Item Form product split | Architecture; separate from bug IDs SP-001 |
| `modules/*` vs `pages/*` duplicate routers | Refactor; use `pages` only when touching handoffs |

---

## Quick reference: phase → bug IDs

| Phase | Bug IDs |
|-------|---------|
| 0 | PP-001, NP-005 |
| 1 | DL-003, SP-001, PP-003, SP-005, NP-004 |
| 2 | XP-001–XP-005, OR-001, SS-002 |
| 3 | SV-001–SV-006 |
| 4 | SS-001, SS-004–SS-006, CD-001–CD-004 |
| 5 | SP-002–SP-004, NP-003 |
| 6 | DL-004, DL-005, SS-004 |
| 7 | DL-001, DL-002, NP-001, NP-002 |

---

*Update this file when phases complete or priorities change. Do not reorder Phase 1 below Phase 3 without cause—handoffs matter less if save paths still fail.*
