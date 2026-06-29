# IPS Operations Platform

Professional Streamlit + Supabase company management app for **Industrial Plant Solutions** — jobs, estimates, inventory, assets, timekeeping, employees, certifications, documents, and company updates.

## One unified company app

This repo is **a single Streamlit application**, not multiple separate apps.

| What | Where |
|------|--------|
| **Main entry point** | `app/main.py` |
| **Start command** | `streamlit run app/main.py` |
| **Navigation / routing** | `app/navigation.py` + `app/phase2.py` |
| **Sidebar** | `app/components/sidebar.py` |
| **Auth & session** | `app/auth.py` (gate only in `main.py`) |
| **Supabase** | `app/db.py` (`get_client()` / `get_admin_client()`) |
| **Theme / CSS** | `app/styles.py` (`inject_global_css()` on every module) |

Each business area is a **module/page** inside that shell — Jobs, Estimates, **Pricing Guide**, Inventory, Assets, Timekeeping, Users/Employees, Reports, etc. They are not standalone Streamlit apps.

### Pricing Guide vs Inventory vs Estimate Materials

| Concept | Purpose | Primary table(s) |
|---------|---------|------------------|
| **Pricing Guide** | Master catalog of default costs (material, labor, equipment, travel, etc.) | `pricing_guide_items` (legacy merge from `estimate_materials` if migration missing) |
| **Inventory** | Physical stock on hand — QR tracking, check-in/check-out, job issue transactions | `inventory_items` |
| **Estimate Materials** | Material **lines on a specific estimate** (cost builder) | `estimate_line_items` |

The Pricing Guide can set optional/mandatory stock policy and quantity on hand inline; linked rows sync to `inventory_items`. Inventory remains a separate module for shop/field scans and transactions.

Helper launchers (`run_streamlit.ps1`, `run_streamlit.bat`, `run_app.py`) all start the same `app/main.py`. See [LAUNCHERS.md](LAUNCHERS.md).

## Features

- Fixed left sidebar with logo and user profile
- Consistent SaaS dashboard UI (cards, filters, selectable tables, detail panels)
- Role-based access (Admin, Supervisor, Project Manager, Employee, Viewer)
- Supabase-backed data with **Live data** / **Sample data** badges on Dashboard and Reports when tables are empty or unreachable
- Field Supervisor Mode for tablet-friendly job lookup and time entry
- Pipeline view for quotes → jobs workflow
- Centralized CSS in `app/styles.py` (injected on every page)

## Folder structure

```
app/
  main.py              # ONLY entry: auth gate, sidebar, render module
  navigation.py        # Slug routing + legacy label mapping
  auth.py              # Login, session, cookies, roles
  config.py            # Settings from .env / st.secrets
  db.py                # Cached Supabase client (all modules)
  styles.py            # Global CSS (all modules)
  phase2.py            # Module registry → render()
  components/          # Shared UI (sidebar, tables, cards, …)
  pages/               # Page modules: dashboard.py, jobs.py, …
    _core/             # Shared page helpers (_data, _access, _session)
    modules/           # Legacy copies (not routed — use pages/*.py)
    _legacy/           # Old screens (not routed)
  services/            # Supabase reads/writes per domain
  utils/               # constants, permissions, formatting, dates
.streamlit/
  config.toml          # showSidebarNavigation = false (single app)
  secrets.toml.example
sql/                   # Supabase migrations
```

## Setup

1. **Clone** and create a virtual environment (Python 3.11+ recommended):

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. **Secrets** — choose one:

   - Copy `.streamlit/secrets.toml.example` → `.streamlit/secrets.toml`, or
   - Copy `.env.example` → `.env` at the project root

   ```ini
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_PUBLISHABLE_KEY=your-publishable-or-anon-key
   ```

   Optional (server only): `SUPABASE_SERVICE_ROLE_KEY`

3. **Database** — run SQL migrations in Supabase SQL editor in order (`sql/MIGRATION_ORDER.md`), including `062_phase3_operations_hub.sql`.

4. **Run** (from project root):

   ```powershell
   streamlit run app/main.py
   ```

   Optional helpers (same app): `.\run_streamlit.ps1`, `run_streamlit.bat`, or `python run_app.py` for hosting.

   Open http://localhost:8501

## GitHub SSH workflow

```powershell
git init
git remote add origin git@github.com:USER/REPO.git
git add .
git commit -m "Rebuild IPS operations app"
git push -u origin main
```

Never commit `.env`, `.streamlit/secrets.toml`, or service-role keys.

Verify locally (should print *passed*):

```powershell
python scripts/verify_no_secrets_tracked.py
git check-ignore -v .streamlit/secrets.toml
```

If real keys were ever committed or shared in chat, rotate them in the Supabase dashboard immediately.

## Database assumptions

See [SUPABASE_SCHEMA_NOTES.md](SUPABASE_SCHEMA_NOTES.md) for table/column mappings. Core tables:

| Area | Tables |
|------|--------|
| Jobs | `jobs` |
| Estimates | `estimates`, `estimate_line_items` |
| Pricing Guide | `pricing_guide_items` |
| Inventory | `inventory_items`, `inventory_transactions` |
| Assets | `assets` |
| Time | `employee_timekeeping_weeks`, `time_entries` |
| People | `employees`, `profiles`, `employee_certifications`, `employee_documents` |
| Docs | `documents_hub` |
| Updates | `company_updates` |
| Tasks | `todos` |
| Lookups | `ips_lookup_tables`, `ips_lookup_values` |

**Storage buckets** (create in Supabase when using uploads): `certification-documents`, `employee-documents`, plus buckets used by job photos and inventory images (see service modules).

## Documentation

- [docs/KNOWN_DATA_BUGS.md](docs/KNOWN_DATA_BUGS.md) — data-flow bug tracker (open / fixed)
- [docs/FIX_ORDER.md](docs/FIX_ORDER.md) — recommended repair sequence
- [docs/CURRENT_APP_FLOW.md](docs/CURRENT_APP_FLOW.md) — as-built module behavior
- [TESTING_CHECKLIST.md](TESTING_CHECKLIST.md)
- [DEPLOYMENT_NOTES.md](DEPLOYMENT_NOTES.md)
- [app/pages/LEGACY_PAGES.md](app/pages/LEGACY_PAGES.md)

## Security

- Row Level Security should be enabled in Supabase for production.
- HR documents: Admin only for restricted files; supervisors see field certifications; employees see own records.
- Keys loaded only via `app/config.py` from environment or Streamlit secrets.
