"""Patch job_database.py to use the modern UI module."""
import sys

path = r"C:\IPS APP\app\pages\job_database.py"

with open(path, "r", encoding="utf-8") as f:
    src = f.read()

original_len = len(src)
print(f"Original length: {original_len}")

# ── 1. Add import after crud-list-styles import ───────────────────────────
IMPORT_OLD = "from ips_crud_list_styles import inject_ips_crud_list_styles  # type: ignore"
IMPORT_NEW = (
    "from ips_crud_list_styles import inject_ips_crud_list_styles  # type: ignore\n"
    "\n"
    "try:\n"
    "    from app.pages.job_database_modern_ui import inject_modern_jobs_css as _jmod_inject_css\n"
    "    from app.pages.job_database_modern_ui import render_jobs_table as _render_modern_jobs_table\n"
    "except ImportError:\n"
    "    from pages.job_database_modern_ui import inject_modern_jobs_css as _jmod_inject_css  # type: ignore\n"
    "    from pages.job_database_modern_ui import render_jobs_table as _render_modern_jobs_table  # type: ignore"
)

if IMPORT_OLD in src:
    src = src.replace(IMPORT_OLD, IMPORT_NEW, 1)
    print("Step 1: import added OK")
else:
    print("ERROR: import anchor not found", file=sys.stderr)
    sys.exit(1)

# ── 2. Replace table block + action bar (up to the delete-confirm block) ─────
TABLE_START = '                if "id" not in df_display.columns:'
TABLE_END   = '            pend = st.session_state.get(IPS_PENDING_DELETE) or {}'

si = src.find(TABLE_START)
ei = src.find(TABLE_END)
print(f"Step 2: table block {si} -> {ei}")

if si < 0 or ei <= si:
    print("ERROR: table block boundaries not found", file=sys.stderr)
    sys.exit(1)

REPLACEMENT = (
    '                if "id" not in df_display.columns:\n'
    '                    st.dataframe(df_display[visible_cols], use_container_width=True, hide_index=True)\n'
    '                elif use_table:\n'
    '                    _jmod_inject_css()\n'
    '                    _render_modern_jobs_table(\n'
    '                        df_display=df_display,\n'
    '                        job_num_col=job_num_col,\n'
    '                        can_edit=can_edit,\n'
    '                        jobs=jobs,\n'
    '                        admin_read=admin_read,\n'
    '                        customer_name_by_id=customer_name_by_id,\n'
    '                    )\n'
    '                else:\n'
    '                    clear_selected_ids(TABLE_KEY_JOBS)\n'
    '                    _render_job_card_list(\n'
    '                        df_display=df_display,\n'
    '                        job_num_col=job_num_col,\n'
    '                        can_edit=can_edit,\n'
    '                    )\n'
    '\n'
    '            '
)

src = src[:si] + REPLACEMENT + src[ei:]
print("Step 2: table block replaced OK")

# ── 3. Remove unused `picked` declaration ────────────────────────────────────
PICKED = "\n            picked: list[str] = []\n"
if PICKED in src:
    src = src.replace(PICKED, "\n", 1)
    print("Step 3: picked removed OK")
else:
    print("Step 3: picked not found (already clean or different whitespace)")

# ── 4. Write file ─────────────────────────────────────────────────────────────
with open(path, "w", encoding="utf-8") as f:
    f.write(src)
print(f"Written. New length: {len(src)} (delta: {len(src)-original_len:+d})")
