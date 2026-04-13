# Advanced Asset Module

This package adds a production-ready asset module structure for a Streamlit + Supabase app.

Included:
- SQL table setup
- Streamlit pages
- service files
- save logic
- duplicate checker
- maintenance tracker

## Suggested pages
- Asset Dashboard
- Asset Intake
- Asset Database
- Asset Assignments
- Asset Maintenance
- Asset Inspections
- Asset Documents

## How to integrate
1. Copy `sql/*.sql` into your Supabase project and run them.
2. Copy `app/pages/*.py` and `app/services/*.py` into your app.
3. Add the pages to your `main.py` page registry.
4. Ensure your existing `db.py` exposes:
   - `fetch_table`
   - `fetch_by_match`
   - `fetch_one`
   - `insert_row`
   - `update_rows`
   - `upload_bytes` (optional, for photos/documents)

## Expected existing helpers
These pages assume you already have:
- `branding.render_header`
- `auth.current_profile`
- `auth.current_role`
- `db.py` helper functions

## Notes
- This module is written to match your existing app style.
- Duplicate detection is conservative by default.
- Maintenance due logic supports hours, mileage, and dates.
