# AGENTS.md

## Cursor Cloud specific instructions

### Overview

This is a monolithic **Streamlit + Supabase** web application for IPS (Industrial Plant Solutions) company operations management. Single entry point: `app/main.py`.

### Running the application

```bash
export PATH="$HOME/.local/bin:$PATH"
streamlit run app/main.py --server.headless=true --server.port=8501
```

The app will be available at `http://localhost:8501`. It requires valid `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` environment variables (injected as secrets).

### Running tests

The project uses stdlib `unittest` (no pytest in dependencies):

```bash
python3 -m unittest tests.test_verify_no_secrets_tracked -v
```

### Linting

No linter is configured in this repository. Use `python3 -c "import py_compile; py_compile.compile('app/main.py', doraise=True)"` for basic syntax checks if needed.

### Key caveats

- The `streamlit` and other script executables install to `~/.local/bin` — always ensure `PATH` includes that directory.
- The app requires Supabase credentials to show the login page. Without them, `validate_supabase_public_config()` raises an error.
- Authentication is handled entirely by Supabase Auth — there is no local user database.
- The app has demo/fallback data for some modules when Supabase tables are missing, but login still requires a valid Supabase project with user accounts.
- Python 3.12 is used in this environment (production uses 3.11.9 per `runtime.txt`; both are compatible).
