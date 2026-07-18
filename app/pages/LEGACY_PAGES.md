# Page modules vs legacy code

## One unified app

Everything routes through **`app/main.py`** → **`app/navigation.py`** / **`app/phase2.py`** → **`app/pages/<module>.py`**.

There is only one `st.set_page_config` and one sidebar (`app/components/sidebar.py`).

## Active modules (routed)

Registered in `app/phase2.py` → `BUILT_MODULES`. Each slug maps to a single `render()` in `app/pages/<slug>.py` (Phase 2B implementation).

| Slug | Entry |
|------|--------|
| `dashboard` | `pages/dashboard.py` |
| `jobs` | `pages/jobs.py` |
| `customers` | `pages/customers.py` |
| `estimates` | `pages/estimates.py` |
| `pricing_guide` | `pages/pricing_guide.py` |
| `estimate_materials` | `pages/estimate_materials.py` |
| `inventory` | `pages/inventory.py` |
| `assets` | `pages/assets.py` |
| `timekeeping` | `pages/timekeeping.py` |
| `weekly_timesheets` | `pages/weekly_timesheets.py` |
| `employees` / `users` | `pages/employees.py` |
| `employee_certifications` | `pages/employee_certifications.py` |
| `employee_documents` | `pages/employee_documents.py` |
| `company_updates` | `pages/company_updates.py` |
| `tasks` | `pages/tasks.py` |
| `documents` | `pages/documents.py` |
| `reports` | `pages/reports.py` |
| `admin` | `pages/admin.py` |
| `settings` | `pages/settings.py` |
| Field ops | `pages/field_*.py`, `pages/coupling_inspection.py` |

Shared data layer: `app/pages/_core/_data.py`, `_session.py`, `_access.py`, `_crud.py`.

## Special routes (not sidebar modules)

| File | Used by |
|------|---------|
| `inventory_scan.py` | `main.py` — QR/deep link |
| `asset_scan.py` | `main.py` — asset QR deep link |
| `install_app.py` | `main.py` — PWA install |
| `sign_timesheet.py` | `main.py` — public `?tsign=<uuid>` |

## Helper / redirect pages (not sidebar entry points)

Imported by active code or used for deep links — **do not** `streamlit run` these directly:

- `estimate_editor.py` — shim re-exporting `app/estimate/*` (PDF import, persistence)
- `estimate_builder_ui.py` — estimate worksheet tabs used by `pages/estimates.py`
- `asset_kits_ui.py` — kit UI helpers imported by `pages/assets.py`
- `app/ui/` — navigation session keys for pending deep links

## Removed dead trees (2026)

The following were deleted after confirming they were not imported by active routes:

- `pages/modules/` — early Phase 2 prototype, never wired in `phase2.py`
- `pages/_legacy/` — pre-unification full-page UIs
- `pages/customers_jobs.py`, `pages/time_tracking.py` — unwired duplicates
- `app/estimates/` — alternate estimates UI package (superseded by `pages/estimates.py`)
- Tier 1 unwired pages — standalone `render()` modules never in `phase2.py`: `supervisor_planning.py`, `po_expenses.py`, `employee_toolbox.py`, `asset_detail.py`, `asset_intake.py`, `asset_scanner.py`, `asset_assignments.py`, `asset_maintenance.py`, `asset_inspections.py`, `asset_documents.py`, `inventory_supplies.py`, `material_quote_import.py`, `tool_trailer_audits.py`, `pm_matrix_entry.py`, `pm_matrix_time.py`, `labor.py`, and the job-database UI cluster (`job_database_*.py`, `job_reference_attachments_ui.py`)
- `job_costing.py` — removed; Job Costing lives in Jobs detail (`job_costing_tab.py`) via `navigation.open_jobs_job_costing`
- `legacy_sidebar.py`, `_import_render.py` — removed; superseded by `sidebar_shell.py` and lazy `phase2` registry
