-- Estimate → job approval workflow columns.
-- Safe to re-run (ADD COLUMN IF NOT EXISTS).

alter table if exists public.estimates
    add column if not exists job_id uuid references public.jobs (id) on delete set null;

alter table if exists public.estimates
    add column if not exists approved_at timestamptz;

alter table if exists public.estimates
    add column if not exists approved_by uuid;

alter table if exists public.estimates
    add column if not exists converted_to_job_at timestamptz;

alter table if exists public.estimates
    add column if not exists archived_from_estimates boolean not null default false;

create index if not exists idx_estimates_archived_from_estimates
    on public.estimates (archived_from_estimates);

create index if not exists idx_estimates_approved_at
    on public.estimates (approved_at);

alter table if exists public.jobs
    add column if not exists estimate_id uuid references public.estimates (id) on delete set null;

alter table if exists public.jobs
    add column if not exists approved_at timestamptz;

alter table if exists public.jobs
    add column if not exists approved_by uuid;

alter table if exists public.jobs
    add column if not exists source_estimate_number text not null default '';

create index if not exists idx_jobs_source_estimate_number
    on public.jobs (source_estimate_number);

comment on column public.estimates.archived_from_estimates is
    'When true, hide from default Active Estimates list after approval/conversion.';
comment on column public.jobs.source_estimate_number is
    'Original estimate quote/estimate number when job was created from an estimate.';
