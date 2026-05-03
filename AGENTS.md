# AGENTS.md

## Cursor Cloud specific instructions

### Product overview

IPS-APP is a Streamlit-based industrial plant services management application (estimating, job management, asset tracking, inventory, time tracking, etc.) backed by **Supabase** (PostgreSQL + Auth + Storage). It is a single Python service — not a monorepo.

### Running the app

```bash
streamlit run app/main.py --server.port=8501 --server.address=0.0.0.0
```

The app listens on port 8501 by default. The alternative launcher `python run_app.py` starts Streamlit on port `$PORT` (default 10000) with `developmentMode=false`.

### Required environment variables

The Supabase secrets below must be set (injected as Cloud Agent secrets):

- `SUPABASE_URL`
- `SUPABASE_PUBLISHABLE_KEY` (or legacy `SUPABASE_ANON_KEY`)
- `SUPABASE_SECRET_KEY` (or legacy `SUPABASE_SERVICE_ROLE_KEY`)

A `.env` file in the repo root is loaded automatically by `app/config.py`. Set `APP_ENV=development` and `APP_BASE_URL=http://localhost:8501` for local development.

### Linting

No lint configuration is committed to the repo. Use `ruff` for quick lint checks:

```bash
ruff check app/
```

The codebase has pre-existing lint issues (unused imports, etc.) — these are not regressions.

### Testing

There is **no test suite** in this repository — no pytest, unittest, or test files. Verification is done by running the app and testing manually.

### Key gotchas

- **PyJWT conflict**: The system-installed `PyJWT 2.7.0` cannot be uninstalled normally because it lacks a RECORD file. Run `pip install --ignore-installed pyjwt` before `pip install -r requirements.txt` to work around this.
- **Streamlit first-run prompt**: On first launch, Streamlit asks for an email. Send an empty response (press Enter) to skip it. Setting `STREAMLIT_BROWSER_GATHER_USAGE_STATS=false` in the environment or using the `.streamlit/config.toml` (already committed) suppresses this.
- **Deprecation warnings**: Streamlit logs `Please replace st.components.v1.html with st.iframe` — these are harmless warnings from the current Streamlit version.
- **Python version**: `.python-version` says 3.11.9 but the app works fine on Python 3.12.x (used in production on Render and in the Cloud Agent VM).
- **No Docker required**: This is a pure Python app. No Docker, no docker-compose.
- **`app/` is on `sys.path`**: Streamlit adds the script's directory to `sys.path`, so modules in `app/` import each other without the `app.` prefix (e.g., `from auth import ...` not `from app.auth import ...`).
