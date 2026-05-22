# Supabase schema notes (rebuilt app)

## Required core tables

**New projects:** run **`sql/001_core.sql`** through **`sql/011_phase3_schema_align.sql`** in order (see **`sql/MIGRATION_ORDER.md`**).

**Existing projects:** may use **`sql/000_core_bootstrap.sql`** + legacy files + **`sql/062_phase3_operations_hub.sql`**.

See **`sql/MIGRATION_ORDER.md`** for full dependency tiers and run order.

| Table | Used by |
|-------|---------|
| `customers` | Customers, Jobs, Estimates, Locations |
| `vendors` | Vendors (master; distinct from lookup seeds) |
| `departments` | Org units (optional; employees still use text `department`) |
| `jobs` | Jobs, Timekeeping, Reports |
| `estimates` | Estimates, Estimate Materials, Reports |
| `employees` | Employees, Timekeeping, Certifications |
| `customer_locations` | Sites per customer |
| `profiles` | Auth / roles |
| `inventory_items` | Inventory (alias: `inventory`) |
| `assets` | Assets |
| `time_entries` | PM matrix timekeeping |
| `company_updates` | Company Updates |
| `todos` | Tasks (alias: `tasks`) |

## Phase 3 migration (`sql/062_phase3_operations_hub.sql`)

| Table | Purpose |
|-------|---------|
| `ips_lookup_tables` | Lookup group definitions |
| `ips_lookup_values` | Dropdown values (Admin-managed) |
| `documents_hub` | Central document repository |
| `employee_certifications` | HR certifications |
| `employee_documents` | Per-employee files |
| `estimate_line_items` | Estimate material lines (UI tab) |
| `employee_timekeeping_weeks` | Weekly approval summary |
| `employee_timekeeping_days` | Daily ST/OT/DT grid (schema ready) |

## Column mapping (app ↔ DB)

- **Jobs:** `notes` stores description; `customer_name` → UI `customer`
- **Estimates:** `quote_number` → UI `estimate_number`; `message` → company update body
- **Tasks:** `todos` — UI `Done` maps to DB `Complete`; `Medium` priority → `Normal`
- **Company updates:** `message` column (not `body`)

## Phase 3 app wiring (services)

- Pages call **`app/pages/_core/_data.py`** → **`app/services/*_service.py`** → **`phase2_modules_service.py`** → **`repository.py`**.
- Mutations call **`clear_all_data_caches()`** after insert/update/delete.
- Demo row IDs (`demo-*`) are blocked from writes with a clear message; demo lists still load when tables are missing.

## Demo data behavior

- Demo/sample rows load **only** when PostgREST returns an error (404, missing relation, RLS denial surfaced as error).
- An **empty** successful query shows an empty table — not demo data.

## RLS

Migration `062` uses permissive `authenticated` policies for new tables. Tighten policies before production.

## Apply order

**Do not rely on numeric filename order alone** — several files assume parents that were never created in-repo.

1. Run **`sql/000_core_bootstrap.sql`** (customers → vendors → departments → employees → locations → jobs → estimates → inventory → assets → time_entries → profiles).
2. Follow **`sql/MIGRATION_ORDER.md`** (recommended sequence; skip `008`/`009` on fresh DBs).
3. Run **`sql/062_phase3_operations_hub.sql`** last.
4. Seed `ips_lookup_values` via Admin UI or SQL inserts.
