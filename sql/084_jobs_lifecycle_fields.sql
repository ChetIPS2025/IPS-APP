-- =============================================================================
-- 084_jobs_lifecycle_fields.sql — Job complete / cancel / soft-delete audit fields
-- Depends on: 002_jobs.sql
-- =============================================================================

alter table public.jobs
    add column if not exists completed_at timestamptz,
    add column if not exists completed_by uuid references public.profiles (id) on delete set null,
    add column if not exists cancelled_at timestamptz,
    add column if not exists cancelled_by uuid references public.profiles (id) on delete set null,
    add column if not exists cancellation_reason text,
    add column if not exists is_deleted boolean not null default false,
    add column if not exists deleted_at timestamptz,
    add column if not exists deleted_by uuid references public.profiles (id) on delete set null,
    add column if not exists delete_reason text;

create index if not exists idx_jobs_is_deleted on public.jobs (is_deleted);
create index if not exists idx_jobs_completed_at on public.jobs (completed_at desc nulls last);

comment on column public.jobs.is_deleted is 'Soft-delete flag; archived jobs remain for history.';
comment on column public.jobs.completed_at is 'When the job was marked Completed.';
comment on column public.jobs.cancelled_at is 'When the job was marked Cancelled.';
