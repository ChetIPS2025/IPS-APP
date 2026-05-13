-- Narrative scope fields on estimates (Job Scope tab persistence).
-- Safe to re-run.

alter table if exists public.estimates
    add column if not exists scope_of_work text;

alter table if exists public.estimates
    add column if not exists customer_responsibilities text;

alter table if exists public.estimates
    add column if not exists updated_at timestamptz;

comment on column public.estimates.scope_of_work is
    'Plain-text scope of work shown on proposals and Job Scope tab.';
comment on column public.estimates.customer_responsibilities is
    'Plain-text customer responsibilities shown on proposals and Job Scope tab.';
