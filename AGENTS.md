# AGENTS.md

## Cursor Cloud specific instructions

### Overview

IPS-APP is a Streamlit-based business management application for Industrial Plant Solutions, LLC. It uses Supabase (hosted PostgreSQL + Auth + Storage) as the backend and OpenAI for optional AI features.

### Running the application

```bash
source /workspace/.venv/bin/activate
export PYTHONPATH="/workspace:/workspace/app"
streamlit run app/main.py --server.address=0.0.0.0 --server.port=10000
```

The `PYTHONPATH` must include both `/workspace` and `/workspace/app` because the codebase uses a mix of absolute imports (`from app.config import settings`) and relative/bare imports (`from config import settings`). Without both paths, you will see `ModuleNotFoundError`.

### Required secrets

The app requires these environment variables (set as Cursor secrets):

| Variable | Purpose |
|----------|---------|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_PUBLISHABLE_KEY` | Public/anon key for client Supabase access |
| `SUPABASE_SECRET_KEY` | Service role key for admin operations |

Legacy aliases `SUPABASE_ANON_KEY` and `SUPABASE_SERVICE_ROLE_KEY` are also supported.

`OPENAI_API_KEY` is optional (only needed for PDF import / AI features).

### Linting and testing

There are no automated tests or linting configuration in this repository. To verify code correctness, import all modules:

```bash
source /workspace/.venv/bin/activate
PYTHONPATH="/workspace:/workspace/app" python -c "import app.main"
```

### Key caveats

- Python 3.11 is required (specified in `.python-version`). The system default is 3.12 which is not compatible.
- The virtual environment is at `/workspace/.venv` using `python3.11`.
- The Streamlit email prompt on first run can be skipped by pressing Enter or by setting `gatherUsageStats = false` in `~/.streamlit/config.toml` (already set in the repo's `.streamlit/config.toml`).
- No Docker, no Makefile, no devcontainer — setup is simply `pip install -r requirements.txt` in a Python 3.11 venv.
