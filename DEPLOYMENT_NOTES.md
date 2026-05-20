# Deployment notes

## Environment variables

Set in the host (Render, VM, etc.) or `.env` locally — **never commit** real keys.

| Variable | Required | Notes |
|----------|----------|-------|
| `SUPABASE_URL` | Yes | Project URL |
| `SUPABASE_PUBLISHABLE_KEY` or `SUPABASE_ANON_KEY` | Yes | Browser-safe key |
| `SUPABASE_SERVICE_ROLE_KEY` | Admin ops | Server-only; optional for invites |
| `APP_BASE_URL` | Recommended | Used for auth redirects |

Streamlit Cloud: use **Secrets** UI; file maps to `.streamlit/secrets.toml` (gitignored).

## Run locally

```powershell
cd "c:\IPS APP"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Edit .env with your Supabase values
streamlit run app/main.py
```

Or use `run_streamlit.ps1` if present.

## Database

1. Apply SQL migrations under `sql/`.
2. Confirm `062_phase3_operations_hub.sql` for rebuilt modules.
3. Create at least one `profiles` row linked to an auth user with role `admin`.

## Production checklist

- [ ] `.streamlit/secrets.toml` and `.env` not in git
- [ ] Service role key only on server
- [ ] RLS policies reviewed
- [ ] `APP_BASE_URL` matches public HTTPS URL
- [ ] Smoke test `TESTING_CHECKLIST.md`

## Streamlit

- Entry point: `app/main.py`
- Rebuilt UI uses **`app/styles.py`** only (legacy `app/ui/theme.py` not loaded for module routes)
