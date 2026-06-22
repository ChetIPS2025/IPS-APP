-- =============================================================================
-- 118_jobs_projected_financials.sql — Precomputed projected profit/margin on jobs
-- Depends on: 117_jobs_estimated_cost.sql
-- =============================================================================

alter table public.jobs
    add column if not exists projected_gross_profit numeric(14, 2);

alter table public.jobs
    add column if not exists projected_margin_pct numeric(8, 2);

comment on column public.jobs.projected_gross_profit is
    'Contract value minus estimated cost; maintained on save and estimate sync.';

comment on column public.jobs.projected_margin_pct is
    'Projected gross profit as percent of contract value; maintained on save and estimate sync.';
