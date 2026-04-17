-- Optional: adds denormalized preparer fields on estimates for reporting and list views.
-- Run in Supabase SQL after prior migrations. Safe to re-run.

alter table if exists public.estimates
    add column if not exists prepared_by_id text;

alter table if exists public.estimates
    add column if not exists prepared_by_name text;

comment on column public.estimates.prepared_by_id is
    'Preparer reference, e.g. p:<profile_uuid> or e:<employee_uuid>; may hold a legacy display string if only one text column existed.';
comment on column public.estimates.prepared_by_name is
    'Human-readable preparer label shown on proposals and reports.';
