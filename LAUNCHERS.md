# How to start the IPS app

This repository contains **one** Streamlit application. All business modules share the same entry point, auth, Supabase client, CSS, and sidebar.

## Primary command (use this)

From the project root (`IPS APP/`):

```powershell
streamlit run app/main.py
```

## Helper scripts (same app — not separate apps)

| File | Purpose |
|------|---------|
| `run_streamlit.ps1` | Windows PowerShell helper; runs `streamlit run app/main.py` from repo root |
| `run_streamlit.bat` | Windows batch helper; same as above |
| `run_app.py` | Hosting launcher (Render/Docker); sets `PORT` and `0.0.0.0`, then runs `app/main.py` |

Do **not** run legacy page files under `app/pages/_legacy/` or old screens like `job_database.py` directly — they are not entry points.

## Not used

- Streamlit multipage `pages/` auto-discovery (disabled via `.streamlit/config.toml` → `showSidebarNavigation = false`)
- Separate Streamlit apps per module (Jobs, Estimates, etc. are **modules** inside `app/main.py`)
