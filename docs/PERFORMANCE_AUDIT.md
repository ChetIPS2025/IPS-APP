# IPS Streamlit Application — Performance & Dead-Code Audit (Phase 1)

**Date:** 2026-07-18  
**Branch audited:** `main` (commit `89cc97f` area)  
**Scope:** Analysis only — no production behavior changes, deletions, dependency removals, or schema changes.

---

## Executive summary

The IPS app is a single-process Streamlit shell (`app/main.py`) routing 33 modules through `app/phase2.py`. Cold startup pays a **~2.1 s import tax** because **every page module is imported eagerly**, pulling in pandas/numpy (~55 ms), reportlab (~84 ms), openpyxl (~85 ms), and heavy page subgraphs (`jobs` ~209 ms, `estimates` ~101 ms cumulative).

The largest runtime costs are **full-catalog Supabase reads** (500–5000 rows) with **client-side filtering/pagination**, **triple-layer caching** (`@st.cache_data` + session catalog mirror + `page_data_cache`), and **full-page reruns** where fragment reruns or `st.form` would suffice.

Highest-impact Phase 2 work:

| Priority | Item | Expected benefit |
|----------|------|------------------|
| **P0** | Lazy page registry via `importlib` | ~1–2 s cold start; lower memory |
| **P1** | Server-side list filtering/pagination for jobs/estimates/customers | Fewer bytes + faster filter clicks |
| **P1** | Consolidate modal/dialog CSS + table bridge factory | Less CSS injection per rerun |
| **P2** | Remove dead modules (`legacy_sidebar.py`, standalone job_costing) | ~50 KB+ code, clearer nav |
| **P2** | Split `styles.py` (14,624 lines) and mega pages | Maintainability |

---

## 1. Project artifacts

### `.gitignore` coverage

`.gitignore` correctly excludes: `.venv/`, `__pycache__/`, `.env`, `.env.*`, `.streamlit/secrets.toml`, `.pytest_cache/`, `dist/`, `build/`, `output/`, `tmp/`, `*.exe`, `*.pkg`, `*.zip`, generated CSS capture files.

**Gaps / notes:**

| Pattern | In `.gitignore`? | Notes |
|---------|------------------|-------|
| `importtime.txt` | No | Local profiling artifact from this audit — add or delete locally |
| `*.pdf` (generated) | No (only dirs) | `output/` ignored, but see tracked PDF below |
| `.mypy_cache/`, `.ruff_cache/` | Yes | |
| Duplicate `build/` / `dist/` entries | Yes (duplicated lines 17–18 and 29–30) | Harmless |

### Artifact classification

| Artifact | Safe to delete locally | Required locally | Required in GitHub | Required on Render | Status |
|----------|------------------------|------------------|--------------------|--------------------|--------|
| `.venv/` | Yes (recreate with pip) | Yes (dev) | No | Built by Render | Ignored ✓ |
| `__pycache__/`, `*.pyc` | Yes | Auto-generated | No | Auto-generated | Ignored ✓ |
| `.pytest_cache/` | Yes | After test runs | No | No (unless CI) | Ignored ✓; **locally present** |
| `build/`, `dist/`, `tmp/`, `output/` | Yes (except committed docs) | Optional | No | No | Ignored ✓ |
| `.env`, `.streamlit/secrets.toml` | Never delete secrets | Yes (local/prod secrets) | **Never** | Env vars on Render | Ignored ✓; **exist locally only** |
| Generated PDFs/ZIPs/exes | Yes | Only when testing exports | No | No | Ignored ✓ |
| `importtime.txt` | Yes | Profiling only | No | No | **Untracked local file** |

### Accidentally tracked files

| Path | Issue | Recommendation (Phase 2) |
|------|-------|----------------------------|
| `output/pdf/app_summary_one_page.pdf` | Under `output/` but **committed** | Remove from git; keep in `.gitignore` |
| PNG/PDF branding in `assets/` | Intentional static assets | Keep; see §9 for size duplicates |
| PWA icons in `app/static/`, `.streamlit/static/` | Required for deploy | Keep |

**Render deploy** (`render.yaml`): `pip install -r requirements.txt` → `python run_app.py`. Needs: app code, `requirements.txt`, static assets, `.streamlit/config.toml` — not `.venv`, caches, or local secrets.

---

## 2. Import performance

### Current architecture

```
app/main.py
  → app/navigation.py (lazy-delegates to phase2)
  → app/phase2.py
       → from app.pages import admin, assets, … (33 modules)
       → BUILT_MODULES: slug → render function
```

**Finding:** `app/phase2.py` **eagerly imports all 33 page packages** at first router use. Every authenticated cold start loads the full module graph regardless of selected slug.

### Import timing measurement

Command run (Windows dev, Python 3.14):

```bash
python -X importtime -c "import app.phase2" 2> importtime.txt
```

| Metric | Value |
|--------|-------|
| **`import app.phase2` cumulative** | **~2,109 ms** |
| Streamlit core | ~130 ms (`streamlit.config`) |
| pandas + numpy | ~55 ms + ~24 ms (via Streamlit/pandas chain) |
| reportlab | ~84 ms (via `weekly_timesheet_export_service` → jobs import chain) |
| openpyxl | ~85 ms (via pandas Excel stack → editor/exports) |
| Per-page cumulative (imported as part of phase2) | |

| Module | Cumulative import time |
|--------|------------------------|
| `app.pages.jobs` | ~209 ms |
| `app.pages.estimates` | ~101 ms |
| `app.pages.assets` | ~25 ms |
| `app.pages.customers` | ~6 ms |
| `app.pages.timekeeping` | ~4 ms |
| `app.pages.inventory` | ~2 ms |
| `app.pages.dashboard` | ~4 ms |
| `app.pages.employees` | ~4 ms |

### Heavy libraries loaded at import time (via page graph)

| Library | Eager on cold start? | Import path | Lazy alternative |
|---------|---------------------|-------------|-------------------|
| **pandas / numpy** | **Yes** | Streamlit + `estimate/editor.py`, `table_actions.py`, job cost tabs | Import inside render/export handlers |
| **reportlab** | **Yes** | `jobs` → `weekly_timesheet_export_service`, `job_weekly_timesheets` | Lazy in export/PDF buttons |
| **openpyxl** | **Yes** | pandas Excel + export services | Lazy in export only |
| **PIL** | Partial | Streamlit image stack | Already lazy in many services |
| **PyMuPDF (fitz)** | No (top-level) | Lazy in `estimate_pdf_import`, `proposal_exports`, `asset_autofill_media` | ✓ Good pattern |
| **pdfplumber / pytesseract** | No | Lazy in `task_attachment_autofill.py` | ✓ |
| **docx / docx2pdf** | No | Lazy in `proposal.py` | ✓ |
| **matplotlib / plotly** | **Not imported in `app/`** | Listed in `requirements.txt` only | **Candidate removal** |

### Top-level module side effects

| File | Side effect at import? |
|------|------------------------|
| `app/phase2.py` | Imports all pages (heavy) |
| `app/pages/_core/_data.py` | Large demo dataset constants (`_DEMO_JOBS`, etc.) — memory only, no DB |
| `app/main.py` | Path setup only until `main()` |
| Page modules | Generally define functions; DB work deferred to `render()` |

### Recommendation: lazy module registry

Replace eager imports in `phase2.py` with:

```python
_MODULE_LOADERS: dict[str, Callable[[], Callable[[], None]]] = {
    "jobs": lambda: __import__("app.pages.jobs", fromlist=["render"]).render,
    ...
}

def render_module(slug: str | None = None) -> None:
    fn = _MODULE_LOADERS.get(active)
    if fn:
        fn()()
```

**Preserve:** `navigation.py` slugs, `ACTIVE_MODULE_SLUGS`, role checks (`role_can_access_page`), deep links (`capture_nav_slug_from_query`, asset/inventory scan embed keys), View As (`render_view_as_page_shell`), Field Mode (`ips_field_mode`), auth gate in `main.py`.

**Risk:** Modules that import each other at top level may need circular-import testing.  
**Tests:** Full pytest suite + smoke test each slug after login.  
**Rollback:** Keep `BUILT_MODULES` dict behind feature flag.

---

## 3. Streamlit rerun audit

### Rerun inventory (approximate)

| Mechanism | Occurrences in `app/` |
|-----------|----------------------|
| `st.rerun()` | ~350+ across 80+ files |
| `ips_app_rerun()` | ~25 (HTML bridges, asset/job/estimate modals) |
| `fragment_rerun()` | ~25 (list fragments) |
| `st.experimental_rerun()` | **0** |

### Classification framework

| Class | When to use | Examples |
|-------|-------------|----------|
| **Required full-app rerun** | `@st.dialog`, cross-fragment state, nav slug change | `ips_app_rerun()` after HTML table open; `navigation.navigate_back()` |
| **Fragment rerun sufficient** | Filter/search/pagination inside `@fragment` | Equipment/assets/inventory/customers list fragments |
| **Automatic callback rerun** | `on_click` / `on_change` without explicit rerun | Hidden bridge buttons (legacy); prefer explicit `ips_app_rerun` for dialogs |
| **Can remove** | Rerun immediately after widget callback that already reruns | Audit per callsite |
| **Move to `st.form`** | Multi-field submit batches | Login email form ✓; timekeeping hour grids (partial) |
| **Move to `@st.dialog`** | Detail panels causing full page reload | Already used for assets/jobs/estimates |

### Priority pages

#### Jobs (`app/pages/jobs.py`)

| Pattern | Count | Classification |
|---------|-------|----------------|
| `st.rerun()` | ~19 | Mix: modal saves, filter clears, detail tabs — many **required full-app** |
| `ips_app_rerun()` | ~6 | **Required** — job detail dialog from HTML bridge |
| `fragment_rerun()` | ~3 | **Correct** — list fragment filter interactions |

**Notes:** List uses `@fragment` + HTML bridge. Detail modal must stay outside fragment. Some `st.rerun()` after `st.session_state` writes in detail tabs could become `fragment_rerun()` if detail moves fully into dialog scope.

#### Assets (`app/pages/assets.py`)

| Pattern | Count | Classification |
|---------|-------|----------------|
| `ips_app_rerun()` | ~3 | **Required** — `@st.dialog` asset detail |
| `fragment_rerun()` | ~2 | **Correct** — equipment/serialized list filters |
| `st.rerun()` | ~5 | Bulk move, kit summary, save paths — review for form batching |

**Recent fix:** Equipment table uses `sendValue` → `handle_assets_table_action` → `ips_app_rerun()` (not hidden-button click).

#### Inventory (`app/pages/inventory.py`)

| Pattern | Count | Classification |
|---------|-------|----------------|
| `fragment_rerun()` | ~1 | Filter bar — **correct** |
| `st.rerun()` | ~8 | Modal saves, QR tab — mostly **required** for dialog |

#### Timekeeping (`app/pages/timekeeping.py`)

| Pattern | Count | Classification |
|---------|-------|----------------|
| `fragment_rerun()` | ~9 | Allocation UI — **correct** |
| `st.rerun()` | ~3 | Week navigation, legacy paths |
| `ips_app_rerun()` | ~1 | Cross-module prefill |

**Concern:** 4,585-line monolith; many widgets outside forms; legacy hour widget keys still read as fallback.

#### Employees (`app/pages/employees.py`)

| Pattern | Count | Classification |
|---------|-------|----------------|
| `ips_app_rerun()` | ~2 | User table bridge → detail |
| `fragment_rerun()` | ~1 | List fragment |
| `st.rerun()` | ~7 | Profile saves |

#### Estimates (`app/pages/estimates.py`)

| Pattern | Count | Classification |
|---------|-------|----------------|
| `st.rerun()` | ~21 | **High** — detail mode, tabs, approvals |
| `ips_app_rerun()` | ~3 | HTML bridge opens |
| `fragment_rerun()` | ~2 | List fragment |

**Opportunity:** Detail view reruns dominate; consolidating detail into `@st.dialog` + fragment list would reduce full-page reloads.

### Unstable dynamic widget keys

| Area | Key pattern | Risk |
|------|-------------|------|
| Timekeeping | `_legacy_hours_widget_key(eid, week_sig, day_ix)` | Medium — migration in progress |
| Table selection | `selected_{table_key}_ids` vs legacy `ips_row_selections` | Low — migration on read |
| Asset modal | `selected_asset_id` parallel to `ips_sel_assets` | Medium — duplicate state |

---

## 4. Database query audit

### Query architecture

```
Page render()
  → load_*() in app/pages/_core/_data.py
    → @st.cache_data (TTL 300s) + _catalog_session_get (session mirror)
    → service.list_* → repository.fetch_rows (default limit 500)
    → db.fetch_table → @st.cache_data (TTL ~30s, auth-scoped)
```

### Catalog limits

| Dataset | Default limit | Client-side filter? |
|---------|---------------|---------------------|
| Jobs | **5000** | Yes — search, view, columns, pagination |
| Estimates | **5000** | Yes |
| Inventory | **500** | Yes |
| Assets | **500** | Yes |
| Employees | **500** | Yes |
| Customers | **500** | Yes |
| Tasks | **500** | Yes |
| Time entries (job costing standalone) | **50000** | Yes |

**Risk:** Inventory/assets/employees/customers may **truncate** silently as data grows while jobs/estimates allow 5000.

### Queries on every rerun (typical list page, warm cache)

| Page | DB hits (cache miss) | Duplicate reads same render |
|------|----------------------|----------------------------|
| **Dashboard** | 4 catalogs + summaries + tasks + activity | `load_jobs()` 2× (KPI + status panel) |
| **Jobs** | 1× jobs; optional 1× tasks | Low |
| **Assets** | 1× assets; +employees/jobs on Serialized tab | Low |
| **Inventory** | 1× enriched (inventory + pricing guide on miss) | QR tab +2 when visible |
| **Timekeeping** | summaries + week batch + optional jobs | Opening N employees → N day queries |
| **Employees** | 1× employees | Docs tab loads **all** documents (500) |
| **Estimates** | 1× estimates | Low on list |
| **Customers** | customers + bulk loc/contacts + jobs + estimates | Two enrichment caches |

### N+1 patterns

| Pattern | Location | Severity |
|---------|----------|----------|
| Customer contact/location by ID | `customers_service.get_customer_contact/location` | **High** — loops customers |
| Per-employee timekeeping grid | `load_timekeeping_grid` | **Medium** |
| All certs/docs for one employee | `load_certifications`, `load_employee_documents` | **Medium** — full table + Python filter |
| All line items for one estimate | `load_estimate_materials` | **Medium** |
| QR history job labels | `qr_scan_event_service` | **Low** — loads 5000 jobs |

### Server-side opportunities (no schema change required for some)

| KPI / operation | Current | Recommended |
|-----------------|---------|---------------|
| Dashboard job counts by status | Client scan of `load_jobs()` | SQL `COUNT(*) GROUP BY status` or RPC |
| Customer open job/estimate counts | Client scan | SQL aggregation |
| List pagination | Client slice after full fetch | Supabase `.range()` + `count` |
| Employee certifications tab | Full table fetch | `fetch_by_match(employee_id=…)` |
| Timekeeping week grid | Per-employee day fetch | Single week query (partially exists) |

### `@st.cache_data` candidates (not yet cached)

| Function | Reason |
|----------|--------|
| `load_recent_qr_scans` | Called on dashboard/inventory; hits DB every time |
| `load_certifications(employee_id)` | Repeated on profile views |
| `load_estimate_materials(estimate_id)` | Repeated on materials tab |

---

## 5. Cache audit

### Layer diagram

```
┌─────────────────────────────────────────────────────────┐
│  @st.cache_data (Streamlit global, TTL 30–300s)         │
│  _data.py catalogs, data_cache.py fetch_table, PG svc   │
└───────────────────────┬─────────────────────────────────┘
                        │ mirrors into
┌───────────────────────▼─────────────────────────────────┐
│  session_state._ips_catalog_datasets                    │
│  (per-user session, until clear_*_catalog_cache)        │
└───────────────────────┬─────────────────────────────────┘
                        │ derived data
┌───────────────────────▼─────────────────────────────────┐
│  page_data_cache (_ips_page_data_cache)                 │
│  dashboard KPIs, customers enriched, inventory enriched │
└───────────────────────┬─────────────────────────────────┘
                        │ modal/detail
┌───────────────────────▼─────────────────────────────────┐
│  Modal caches (session_state per module)                │
│  ASSETS_MODAL_CACHE_KEY, jobs modal, etc.               │
└─────────────────────────────────────────────────────────┘
```

### `@st.cache_data` functions

| Location | Function / key | TTL | Data | Invalidation |
|----------|----------------|-----|------|--------------|
| `_data.py` | `_cached_jobs_rows` | 300s | All jobs | `clear_jobs_catalog_cache()` |
| `_data.py` | `_cached_estimates_rows` | 300s | All estimates | `clear_estimates_catalog_cache()` |
| `_data.py` | `_cached_inventory_rows` | 300s | Inventory items | `clear_inventory_catalog_cache()` |
| `_data.py` | `_cached_assets_rows` | 300s | Assets | `clear_assets_catalog_cache()` |
| `_data.py` | `_cached_employees_rows` | 300s | Employees | `clear_employees_catalog_cache()` |
| `_data.py` | `_cached_customers_rows` | 300s | Customers | `clear_customers_catalog_cache()` |
| `_data.py` | `_cached_tasks_rows` | 300s | Tasks | `clear_tasks_catalog_cache()` |
| `_data.py` | `_cached_user_profiles_rows` | 300s | Profiles | `clear_employees_catalog_cache()` |
| `_data.py` | `_cached_labor_rates_rows` | 300s | Labor rates | `clear_labor_rates_catalog_cache()` |
| `data_cache.py` | `_fetch_table_cached` | ~30s | Raw table rows | `clear_session_table_cache()`, repo writes |
| `pricing_guide_service.py` | `cached_pricing_guide_rows` | 300s | PG items | `clear_pricing_guide_catalog_cache()` |
| `asset_kits_service.py` | kit list | 300s | Kit items | assets cache clear |
| `small_hand_tool_service.py` | hand tools | 300s | Small tools | assets cache clear |

### Session / page caches

| Key | Store | Invalidation | Stale risk |
|-----|-------|--------------|------------|
| `_ips_catalog_datasets` | session | Per-dataset `clear_catalog_session_key` | Medium — survives `@st.cache_data` clear if session key missed |
| `_ips_page_data_cache` | session | Prefix/key clears on catalog invalidation | Medium — customers has **two** enrichment paths |
| `_ips_jobs_list_cost_by_id` | session | `clear_jobs_list_cost_cache()` | Low |
| `ASSETS_MODAL_CACHE_KEY` | session | `invalidate_assets_modal_cache()` | Low |
| `assets_serialized_context` | page_data_cache | `clear_assets_catalog_cache()` | Low |
| `inventory_enriched_rows` | page_data_cache | `clear_inventory_page_data_cache()` | Medium |
| `customers_page_list_rows` | page_data_cache | `clear_customers_page_data_cache()` | Medium |

### Duplicate cache layers (same records)

| Dataset | Layers | Recommendation |
|---------|--------|----------------|
| Jobs | `@st.cache_data` + session mirror + list cost cache | **One authoritative catalog** + derived session indexes |
| Assets | catalog + modal cache + serialized context | Keep modal cache; drop redundant full-list scan in modal resolver |
| Customers | catalog + `customers_enriched_list` + `customers_page_list_rows` | Merge to single enriched cache key |
| Inventory | catalog + enriched rows + pricing guide | Document dependency chain; invalidate together ✓ (mostly) |

### Write-path invalidation

`repository.py` maps table names → `clear_*_catalog_cache()` — recently trimmed (Tier 2) to reduce over-clearing. Unknown tables still fall back to `clear_all_data_caches()`.

**Stale-data risk:** User A saves → cache cleared → User B may still see session mirror until their next write or TTL. Acceptable for internal ops app; document for multi-user editing.

---

## 6. Dependency audit

### `requirements.txt` classification

| Package | Classification | Evidence |
|---------|----------------|----------|
| `streamlit` | **Production required** | Core framework |
| `supabase`, `httpx`, `gotrue` | **Production required** | DB/auth (`db.py` uses `gotrue.SyncMemoryStorage`) |
| `python-dotenv` | **Production required** | Config |
| `Pillow` | **Production required** | Images, QR, thumbnails |
| `qrcode` | **Production required** | Asset/inventory QR |
| `reportlab` | **Production required** | Timesheets, QR labels, inspection PDFs |
| `python-docx` | **Production required** | Proposal generation |
| `docx2pdf` | **Optional feature** | Windows PDF export fallback in `proposal.py` |
| `PyMuPDF` | **Production optional** | Lazy: estimate PDF import, proposals, autofill |
| `PyPDF2` | **Apparently unused** | No imports in `app/` or `tests/` |
| `pdfplumber` | **Optional feature** | `task_attachment_autofill.py` only |
| `pytesseract` | **Optional feature** | OCR autofill; needs Tesseract binary on server |
| `pandas`, `numpy` | **Production required** | Tables, exports, editor — but **over-imported at startup** |
| `openpyxl` | **Production optional** | Excel exports/imports |
| `lxml` | **Transitive / optional** | No direct `app/` imports found |
| `matplotlib`, `plotly` | **Apparently unused** | In requirements; zero `app/` imports |
| `streamlit-drawable-canvas` | **Optional feature** | Signatures: `signature_pad`, timesheets |
| `openai` | **Optional feature** | AI autofill paths |
| `tornado` | **Production required** | Streamlit dependency |
| `setuptools` | **Build/tooling** | Packaging; not runtime-critical on Render |
| `pytest` | **Dev/test only** | Should not be in production install |

### Proposed split

**`requirements.txt` (production):**
```
streamlit>=1.33.0,<2
supabase>=2.8.1,<3
httpx>=0.27.0,<0.29
gotrue>=2.8.1,<3
python-dotenv>=1.0.0,<2
Pillow>=10.0.0,<13
qrcode>=7.4,<8
reportlab>=4.0.0,<5
python-docx>=1.1.0
pandas>=2.1.0,<3
numpy>=1.26.0,<3
tornado
openai==2.32.0
```

**`requirements-dev.txt`:**
```
pytest
ruff
vulture
setuptools>=68.0.0
```

**`requirements-optional.txt`** (document in README; install on Render only if features enabled):
```
PyMuPDF>=1.24.0,<2
pdfplumber>=0.11.0
pytesseract>=0.3.10
docx2pdf>=0.1.8
openpyxl>=3.1.0,<4
streamlit-drawable-canvas>=0.9.0,<1
lxml>=4.9.0,<6
```

**Remove after verification:** `PyPDF2`, `matplotlib`, `plotly` (no imports found).

---

## 7. Dead code and duplication

### Static analysis (Phase 1)

| Tool | Result |
|------|--------|
| `ruff check app tests --select F401,F841` | **239 findings** (mostly unused imports) |
| `vulture app --min-confidence 80` | 23 symbols (unused vars/imports) |

**Note:** Ruff/vulture not in production requirements; installed temporarily for this audit. Do not delete based on Vulture alone.

### High-confidence dead modules

| File | Evidence | Removal risk | Tests |
|------|----------|--------------|-------|
| `app/ui/legacy_sidebar.py` (~889 lines) | Zero imports in repo | **Low** | `test_sidebar_shell.py` |
| `app/pages/_import_render.py` | `load_render()` — zero callers | **Low** | None |
| `app/pages/job_costing.py` standalone UI | `render()` redirects; `_render_standalone_job_costing_page` unreachable | **Medium** | `test_navigation_handoffs.py` |

### Unused wrappers (no production callers)

| File | Symbol |
|------|--------|
| `components/jobs_list_table.py` | `render_jobs_table_link_bridge`, `resolve_jobs_table_link_action` |
| `components/users_list_table.py` | `render_users_table_link_bridge` |
| `components/sidebar_shell.py` | `inject_sidebar_nav_override_css` (inlined elsewhere) |
| `components/assets_page_layout.py` | `inject_assets_page_layout_css` |
| `ui/assets_components.py` | `inject_assets_page_styles` |
| `styles.py` | `inject_assets_module_css` (superseded by `assets_css.py`) |
| `pages/timekeeping.py` | `_render_timekeeping_list_spacer_cell` |

### Duplicate systems

| System | Copies | Consolidation target |
|--------|--------|---------------------|
| HTML table bridges | 8 domain files + `clean_table.py` | Generic bridge factory |
| Modal CSS | `ips_crud_list_styles.py` (v4) + `styles.py` (v5) | Single dialog stylesheet |
| `render_clickable_table` | `tables.py` vs `clickable_table.py` | Rename/disambiguate |
| Logo assets | `company_logo.png` == `ips_logo_wide.png` (both **4954 KB**) | Keep one canonical file |
| Catalog cache | 3 layers (see §5) | Single strategy per dataset |

### Legacy session keys (still read)

| Key | Migration target |
|-----|------------------|
| `selected_asset_id` | `ips_sel_assets` |
| `selected_estimate_id` | `ips_sel_estimates` |
| `ips_row_selections` | `selected_{table}_ids` |
| `ips_jobs_detail_modal_id` + `show_job_detail_modal` | Unified modal key |
| `_ips_scan_legacy_code` | Keep for QR bookmarks |

---

## 8. Large file audit

### Top 30 Python files by line count

| Lines | KB | File | Responsibilities | Split recommendation |
|-------|-----|------|------------------|----------------------|
| 14,624 | 536 | `app/styles.py` | Global + module CSS monolith | **P1 split:** `styles/` package by domain |
| 4,585 | 190 | `app/pages/timekeeping.py` | List, grid, allocation, exports | `timekeeping/` package: page, queries, components, dialogs |
| 2,860 | 119 | `app/pages/estimate_builder_ui.py` | Estimate builder UI | `components/estimate_builder/` |
| 2,688 | 117 | `app/pages/jobs.py` | List, detail modal, tabs | `jobs/page.py`, `jobs/dialogs.py`, `jobs/queries.py` |
| 2,646 | 118 | `app/services/phase2_modules_service.py` | Legacy service hub | Split by domain services |
| 2,638 | 132 | `app/estimate/editor.py` | Estimate editor | Already separate; keep |
| 2,243 | 97 | `app/pages/_core/_data.py` | Catalog loaders + demo data | `data/catalog.py`, `data/demo.py` |
| 2,235 | 102 | `app/pages/customers.py` | CRUD + detail | Split queries/components |
| 2,143 | 89 | `app/components/sidebar_shell.py` | Sidebar + nav rail CSS/JS | Extract CSS to `sidebar_styles.py` |
| 1,999 | 87 | `app/pages/assets.py` | 3 tabs, modals, kits | Partially extracted; continue |
| 1,976 | 80 | `app/db.py` | Supabase client + fetch | `db/client.py`, `db/queries.py` |
| 1,906 | 68 | `app/components/jobs_page_layout.py` | Jobs layout + CSS | Merge with jobs components |
| 1,738 | 77 | `app/pages/inventory_scan.py` | QR scan flow | Standalone — OK |
| 1,691 | 75 | `app/pages/estimates.py` | List + detail | Split detail to `dialogs.py` |
| 1,461 | 64 | `app/services/estimate_costing_service.py` | Costing logic | Keep in services |
| 1,378 | 57 | `app/pages/tasks.py` | Task management | Split components |
| 1,290 | 55 | `app/pages/employee_certifications.py` | Certs CRUD | OK as page |
| 1,154 | 49 | `app/pages/employees.py` | Users/employees | Recently fragmented — model for others |
| 1,029 | 45 | `app/ui/page_header_styles.py` | Header CSS | OK |
| 983 | 41 | `app/auth.py` | Auth/session | OK |

**Target architecture (per module):** `page.py`, `queries.py`, `services.py`, `components.py`, `dialogs.py`, `styles.py`, `calculations.py`.

---

## 9. Static asset and image audit

### Large / duplicate files

| File | Size | Usage | Issue |
|------|------|-------|-------|
| `assets/company_logo.png` | **4954 KB** | `branding.py` fallback chain | **Duplicate of `ips_logo_wide.png`** (identical size) |
| `assets/ips_logo_wide.png` | **4954 KB** | Proposals, headers | Full resolution for web headers |
| `assets/ips_logo_header.png` | 450 KB | Header display | Could be compressed |
| `assets/ips_logo_round.png` | 421 KB | Sidebar/branding | OK |
| `assets/branding/ips_app_icon_source.png` | 434 KB | Icon generation source | OK (source) |
| `app/static/favicon.png` | 2.3 KB | PWA/favicon | ✓ Proper size |
| `app/static/icon-512.png` | 275 KB | PWA | Acceptable |
| `output/pdf/app_summary_one_page.pdf` | 6.9 KB | **Tracked in git** | Should not be committed |

### Thumbnail / URL patterns

| Pattern | Location | Rerun cost |
|---------|----------|------------|
| Signed Supabase URLs | `asset_images.py`, `item_images.py` | Cached in service layer |
| Unified catalog thumbnails | `catalog_images.py` → `get_asset_thumbnail_url` | **Good** — single resolver |
| Base64 inline images | QR/export paths only | Not per-rerun for lists |

### Recommendations

1. Remove duplicate `company_logo.png` vs `ips_logo_wide.png` (keep one, update references).
2. Add compressed web variants (~50 KB) for header logos.
3. Ensure list views always use `catalog_thumbnail_html` (thumbnail=True).
4. Remove `output/pdf/app_summary_one_page.pdf` from git tracking.

---

## 10. Baseline performance report

### Existing instrumentation

Enable with `IPS_DEBUG_PERFORMANCE=1` (or `DEBUG_PERFORMANCE=1`) in environment — see `.env.example`, `app/config.py`, `app/perf_debug.py`.

Logs format: `[perf] {span_name}: {ms} ms` at WARNING level.

### Instrumented spans (already present)

| Span | Location |
|------|----------|
| `module.render:{slug}` | `phase2.py` |
| `page.jobs.render` | `jobs.py` |
| `data.load_jobs/estimates/inventory/assets/employees/customers/tasks` | `_data.py` |
| `customers.enrich_list_rows` | `customers.py` |
| `inventory.enrich_rows` | `catalog_stock_policy_service.py` |
| `repo.clear_*`, `repo.insert_row`, `repo.update_row` | `repository.py` |
| `editor.*` | `estimate/editor.py` |

### Recommended measurement protocol (Phase 1 baseline)

Run locally with Supabase connected:

```bash
set IPS_DEBUG_PERFORMANCE=1
streamlit run run_app.py
```

| Scenario | Actions | Spans to capture |
|----------|---------|------------------|
| **Cold load** | New session, login, land dashboard | Import time + `module.render:dashboard` + all `data.load_*` |
| **Warm load** | Refresh same page | Should show **0 ms** or cache hits for catalogs |
| **Filter interaction** | Assets/Inventory search | Fragment rerun only; no full `data.load_*` |
| **Detail open** | Click asset/job row | `ips_app_rerun` + modal render |
| **Save and refresh** | Edit record, save | `repo.update_row` + cache clear spans |

### Gaps to instrument (Phase 2)

| Area | Suggested span |
|------|----------------|
| Auth bootstrap | `auth.bootstrap` in `main.py` |
| Sidebar render | `sidebar.render` |
| HTML table generation | `table.build_html.{module}` |
| Modal asset lookup | `assets.modal.resolve` |
| Image URL resolution | `images.signed_url` |

**Note:** Phase 1 did not capture live timings (requires running Streamlit with production data). Import timing baseline recorded above (~2.1 s for `app.phase2`).

---

## 11. Prioritized implementation plan

### P0 — Correctness / security

| # | Item | Benefit | Risk | Files | Effort | Tests | Rollback |
|---|------|---------|------|-------|--------|-------|----------|
| P0-1 | Remove `output/pdf/app_summary_one_page.pdf` from git | Smaller repo | Low | git only | 15 min | None | Re-add if needed |
| P0-2 | Verify no secrets tracked | Security | Low | `scripts/verify_no_secrets_tracked.py` | 15 min | Existing script | — |
| P0-3 | Fix customer contact/location N+1 | Correctness + speed | Medium | `customers_service.py` | 2–4 h | Customer tests | Revert query change |

### P1 — Largest measurable speed gains

| # | Item | Benefit | Risk | Files | Effort | Tests | Rollback |
|---|------|---------|------|-------|--------|-------|----------|
| P1-1 | **Lazy `phase2` module registry** | **~1–2 s cold start** | Medium — import cycles | `phase2.py`, `navigation.py` | 4–8 h | Full suite + slug smoke | Feature flag to eager import |
| P1-2 | Lazy pandas/reportlab/openpyxl in page imports | **~200 ms** import reduction | Low | `estimate/editor.py`, job export chain | 4 h | Export tests | Revert lazy imports |
| P1-3 | Server-side pagination for jobs/estimates lists | Faster filter/page | Medium | services + pages | 2–3 d | List/table tests | Client pagination fallback |
| P1-4 | SQL/RPC dashboard KPIs | Dashboard load **−50%+** DB | Medium | `_data.py`, SQL migration | 2 d | Dashboard tests | Keep client fallback |
| P1-5 | Consolidate catalog cache to single layer | Less stale confusion | Medium | `_data.py`, `page_data_cache.py` | 1–2 d | Cache cascade tests | Revert invalidation map |
| P1-6 | Expand `@fragment` + reduce `st.rerun()` on estimates detail | Faster estimate UX | High | `estimates.py` | 3–5 d | Estimates navigation tests | Revert fragment scope |

### P2 — Maintainability / code reduction

| # | Item | Benefit | Risk | Files | Effort | Tests | Rollback |
|---|------|---------|------|-------|--------|-------|----------|
| P2-1 | Delete `legacy_sidebar.py`, `_import_render.py` | **~900 lines** | Low | 2 files | 1 h | Sidebar tests | Git revert |
| P2-2 | Trim `job_costing.py` to redirect-only | **~300 lines** | Medium | `job_costing.py` | 2 h | Navigation tests | Git revert |
| P2-3 | Generic HTML table bridge factory | **~2000 lines** duplicated JS | High | 8 `*_list_table.py` | 3–5 d | All list table tests | Keep old bridges |
| P2-4 | Split `styles.py` into domain modules | Dev velocity | Medium | `app/styles/` | 2–3 d | CSS inject tests | Single file revert |
| P2-5 | Split `timekeeping.py` / `jobs.py` | Maintainability | High | pages packages | 1–2 wk | Timekeeping/jobs suites | Branch isolation |
| P2-6 | Merge modal CSS v4/v5 | Less CSS per rerun | Medium | `styles.py`, `ips_crud_list_styles.py` | 4 h | Visual smoke | Keep both injectors |
| P2-7 | `requirements.txt` / `requirements-dev.txt` split | Faster Render builds | Low | requirements | 1 h | CI install both | Single file |

### P3 — Optional cleanup

| # | Item | Benefit | Risk | Files | Effort |
|---|------|---------|------|-------|--------|
| P3-1 | Remove PyPDF2, matplotlib, plotly from requirements | Smaller install | Low after verify | requirements | 30 min |
| P3-2 | Deduplicate logo PNGs + compress | **~5 MB** git/asset size | Low | `assets/` | 1 h |
| P3-3 | Ruff auto-fix 239 F401/F841 | Cleaner codebase | Low | widespread | 2 h |
| P3-4 | Remove unused bridge wrapper functions | Noise reduction | Low | list_table files | 1 h |
| P3-5 | Add `importtime.txt` to `.gitignore` | Cleaner working tree | None | `.gitignore` | 5 min |

---

## Appendix A — Files generated during this audit

| File | Purpose | Commit? |
|------|---------|---------|
| `importtime.txt` | Import profiling output | **No** — local only |
| `docs/PERFORMANCE_AUDIT.md` | This report | **Yes** |

## Appendix B — Rerun quick reference (priority pages)

| Page | `st.rerun` | `ips_app_rerun` | `fragment_rerun` | Primary pattern |
|------|------------|-----------------|------------------|-----------------|
| Jobs | ~19 | ~6 | ~3 | Fragment list + dialog detail |
| Assets | ~5 | ~3 | ~2 | Fragment list + `@st.dialog` |
| Inventory | ~8 | ~1 | ~1 | Mixed |
| Timekeeping | ~3 | ~1 | ~9 | Fragment-heavy |
| Employees | ~7 | ~2 | ~1 | Fragment list + bridge |
| Estimates | ~21 | ~3 | ~2 | Full-page detail (candidate for dialog) |

## Appendix C — Catalog invalidation map (abbreviated)

See `app/services/repository.py` `_TABLE_CACHE_CLEARERS` for full table→cache mapping. Key clears:

- `jobs` → `clear_jobs_catalog_cache`
- `assets`, `tool_transactions` → `clear_assets_catalog_cache`
- `inventory_items` → `clear_inventory_catalog_cache` + dashboard + inventory page cache
- `estimates` + line-item tables → `clear_estimates_catalog_cache` + dashboard + customers

---

*End of Phase 1 audit. No production code was modified. Review and approve priorities before Phase 2 implementation.*
