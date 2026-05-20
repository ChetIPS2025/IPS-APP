# Page modules vs legacy code

## One unified app

Everything routes through **`app/main.py`** → **`app/navigation.py`** / **`app/phase2.py`** → **`app/pages/<module>.py`** → **`app/pages/modules/<module>.py`**.

There is only one `st.set_page_config` and one sidebar (`app/components/sidebar.py`).

## Active modules (routed)

| Slug | Entry wrapper | Implementation |
|------|---------------|----------------|
| `dashboard` | `pages/dashboard.py` | `pages/modules/dashboard.py` |
| `jobs` | `pages/jobs.py` | `pages/modules/jobs.py` |
| `estimates` | `pages/estimates.py` | `pages/modules/estimates.py` |
| `estimate_materials` | `pages/estimate_materials.py` | `pages/modules/estimate_materials.py` |
| `inventory` | `pages/inventory.py` | `pages/modules/inventory.py` |
| `assets` | `pages/assets.py` | `pages/modules/assets.py` |
| `timekeeping` | `pages/timekeeping.py` | `pages/modules/timekeeping.py` |
| `employees` / `users` | `pages/employees.py`, `pages/users.py` | `pages/modules/employees.py` |
| `employee_certifications` | `pages/employee_certifications.py` | `pages/modules/employee_certifications.py` |
| `employee_documents` | `pages/employee_documents.py` | `pages/modules/employee_documents.py` |
| `company_updates` | `pages/company_updates.py` | `pages/modules/company_updates.py` |
| `tasks` | `pages/tasks.py` | `pages/modules/tasks.py` |
| `documents` | `pages/documents.py` | `pages/modules/documents.py` |
| `reports` | `pages/reports.py` | `pages/modules/reports.py` |
| `admin` | `pages/admin.py` | `pages/modules/admin.py` |
| `settings` | `pages/settings.py` | `pages/modules/settings.py` (delegates to admin UI) |

## Special routes (not sidebar modules)

| File | Used by |
|------|---------|
| `inventory_scan.py` | `main.py` — QR/deep link `?code=INV-…` |
| `sign_timesheet.py` | `main.py` — public `?tsign=<uuid>` (no login) |

## Legacy / helper files (not app entry points)

Still under `app/pages/` for reference or imports from other code — **do not** `streamlit run` these:

- `_legacy/` — old full-page UIs (dashboard, job_database, estimates editor shell, etc.)
- `job_database.py`, `job_database_*.py`, `estimate_editor.py`, `job_costing.py`, …
- `app/ui/` — older navigation helpers; `main.py` still calls `apply_pending_navigation()` for deep links

Safe to migrate or delete only after confirming no imports from services/scripts.
