# IPS APP — Testing Checklist

Use this after configuring Supabase and running `sql/062_phase3_operations_hub.sql`.

## Auth

- [ ] Email login succeeds on first attempt (no second login prompt)
- [ ] “Remember this device” restores session after browser refresh
- [ ] Password reset gate works when `must_reset_password` is set on profile
- [ ] Viewer role cannot open Admin-only pages

## Navigation

- [ ] Sidebar highlights active page
- [ ] Switching pages clears stale row selection where expected
- [ ] Table columns do not collapse after rerun (Jobs, Inventory, Employees)

## Data tables

- [ ] Click **Select** highlights row and opens detail panel below
- [ ] Selected row stays highlighted after unrelated widget interaction
- [ ] Demo banner appears only when Supabase table/query fails (not when table is empty)

## Modules (smoke test each)

- [ ] Dashboard — KPIs and charts render
- [ ] Jobs — filter, select, detail tabs
- [ ] Estimates — list + detail
- [ ] Estimate Materials — lines for active estimate
- [ ] Inventory — low stock statuses
- [ ] Assets — detail panel
- [ ] Timekeeping — week nav, grid, Save Changes
- [ ] Employees — tabs including Certifications / Documents links
- [ ] Employee Certifications — alerts, add form
- [ ] Employee Documents — restricted docs hidden for non-admin
- [ ] Company Updates — metrics, tabs, sidebar panels
- [ ] Documents hub — upload form, module filters
- [ ] Tasks — create task, detail save
- [ ] Reports — sections + CSV download buttons
- [ ] Admin — lookup table editor
- [ ] Settings — application settings tab

## Supabase writes (after migration)

- [ ] Create/update task persists to `todos`
- [ ] Document upload persists to `documents_hub`
- [ ] Certification add persists to `employee_certifications`
- [ ] Timekeeping week save persists to `employee_timekeeping_weeks`

## Security

- [ ] No API keys in repository (`git grep -i supabase` / `eyJ`)
- [ ] `.streamlit/secrets.toml` is gitignored
- [ ] `.env` is gitignored
