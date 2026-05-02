-- Supervisor Daily Planning + PM Goal Review (run after public.jobs exists).
-- Goals, tactical plans, PM reviews, end-of-day reviews.

create table if not exists public.supervisor_goals (
    id uuid primary key default gen_random_uuid(),
    job_id uuid not null references public.jobs (id) on delete cascade,
    supervisor_name text not null default '',
    goal_date date not null,
    goal_type text not null default 'daily' check (goal_type in ('daily', 'weekly')),
    goal_description text not null default '',
    target_quantity numeric(14, 4) null,
    unit text not null default '',
    priority text not null default 'normal' check (priority in ('low', 'normal', 'high', 'critical')),
    due_date date not null,
    created_by uuid null,
    status text not null default 'open' check (status in ('open', 'in_progress', 'completed', 'missed')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_supervisor_goals_job_id on public.supervisor_goals (job_id);
create index if not exists idx_supervisor_goals_due_date on public.supervisor_goals (due_date);
create index if not exists idx_supervisor_goals_goal_date on public.supervisor_goals (goal_date);
create index if not exists idx_supervisor_goals_status on public.supervisor_goals (status);

comment on table public.supervisor_goals is 'PM-set goals for a job/supervisor (daily or weekly window).';

create table if not exists public.supervisor_tactical_plans (
    id uuid primary key default gen_random_uuid(),
    goal_id uuid null references public.supervisor_goals (id) on delete set null,
    job_id uuid not null references public.jobs (id) on delete cascade,
    supervisor_name text not null default '',
    plan_date date not null,
    crew_plan text not null default '',
    first_task text not null default '',
    materials_tools text not null default '',
    known_blockers text not null default '',
    biggest_risk text not null default '',
    confidence text not null default 'medium' check (confidence in ('low', 'medium', 'high')),
    latest_pm_decision text null,
    supervisor_notified_at timestamptz null,
    critical_blocker_flag boolean not null default false,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    created_by uuid null,
    constraint chk_supervisor_tactical_plans_pm_decision check (
        latest_pm_decision is null
        or latest_pm_decision in ('approved', 'needs_adjustment', 'direct_correction')
    )
);

create unique index if not exists uq_supervisor_tactical_plans_job_plan_date
    on public.supervisor_tactical_plans (job_id, plan_date);

create index if not exists idx_supervisor_tactical_plans_goal_id on public.supervisor_tactical_plans (goal_id);

comment on table public.supervisor_tactical_plans is 'Supervisor tactical plan for a calendar work day (one row per job per plan_date).';

create table if not exists public.supervisor_plan_pm_reviews (
    id uuid primary key default gen_random_uuid(),
    plan_id uuid not null references public.supervisor_tactical_plans (id) on delete cascade,
    reviewer_id uuid null,
    decision text not null check (decision in ('approved', 'needs_adjustment', 'direct_correction')),
    hits_goal boolean not null default true,
    crew_utilized boolean not null default true,
    blockers_addressed boolean not null default true,
    pm_notes text not null default '',
    suggested_adjustment text not null default '',
    created_at timestamptz not null default now()
);

create index if not exists idx_supervisor_plan_pm_reviews_plan_id on public.supervisor_plan_pm_reviews (plan_id, created_at desc);

comment on table public.supervisor_plan_pm_reviews is 'PM review of a supervisor tactical plan.';

create table if not exists public.supervisor_eod_reviews (
    id uuid primary key default gen_random_uuid(),
    goal_id uuid not null references public.supervisor_goals (id) on delete cascade,
    plan_id uuid null references public.supervisor_tactical_plans (id) on delete set null,
    job_id uuid not null references public.jobs (id) on delete cascade,
    supervisor_name text not null default '',
    review_date date not null,
    goal_result text not null check (goal_result in ('met', 'partial', 'missed')),
    completed_summary text not null default '',
    delay_reason text not null default 'other' check (
        delay_reason in ('material', 'tools', 'direction', 'rework', 'customer', 'safety', 'equipment', 'other', 'none')
    ),
    delay_within_supervisor_control boolean not null default true,
    tomorrow_plan_needed boolean not null default false,
    photo_urls jsonb not null default '[]'::jsonb,
    score numeric(6, 3) not null default 0,
    score_for_performance numeric(6, 3) not null default 0,
    created_at timestamptz not null default now(),
    created_by uuid null
);

create unique index if not exists uq_supervisor_eod_goal_review_date
    on public.supervisor_eod_reviews (goal_id, review_date);

create index if not exists idx_supervisor_eod_job_review_date on public.supervisor_eod_reviews (job_id, review_date desc);

comment on table public.supervisor_eod_reviews is 'Short end-of-day supervisor review vs goal (scored for performance).';

-- RLS (same posture as sql/045_supervisor_daily_reports.sql)
alter table if exists public.supervisor_goals enable row level security;
drop policy if exists "Allow read access" on public.supervisor_goals;
create policy "Allow read access" on public.supervisor_goals for select to authenticated using (true);
drop policy if exists "Allow insert access" on public.supervisor_goals;
create policy "Allow insert access" on public.supervisor_goals for insert to authenticated with check (true);
drop policy if exists "Allow update access" on public.supervisor_goals;
create policy "Allow update access" on public.supervisor_goals for update to authenticated using (true) with check (true);
drop policy if exists "Allow delete access" on public.supervisor_goals;
create policy "Allow delete access" on public.supervisor_goals for delete to authenticated using (true);

alter table if exists public.supervisor_tactical_plans enable row level security;
drop policy if exists "Allow read access" on public.supervisor_tactical_plans;
create policy "Allow read access" on public.supervisor_tactical_plans for select to authenticated using (true);
drop policy if exists "Allow insert access" on public.supervisor_tactical_plans;
create policy "Allow insert access" on public.supervisor_tactical_plans for insert to authenticated with check (true);
drop policy if exists "Allow update access" on public.supervisor_tactical_plans;
create policy "Allow update access" on public.supervisor_tactical_plans for update to authenticated using (true) with check (true);
drop policy if exists "Allow delete access" on public.supervisor_tactical_plans;
create policy "Allow delete access" on public.supervisor_tactical_plans for delete to authenticated using (true);

alter table if exists public.supervisor_plan_pm_reviews enable row level security;
drop policy if exists "Allow read access" on public.supervisor_plan_pm_reviews;
create policy "Allow read access" on public.supervisor_plan_pm_reviews for select to authenticated using (true);
drop policy if exists "Allow insert access" on public.supervisor_plan_pm_reviews;
create policy "Allow insert access" on public.supervisor_plan_pm_reviews for insert to authenticated with check (true);
drop policy if exists "Allow update access" on public.supervisor_plan_pm_reviews;
create policy "Allow update access" on public.supervisor_plan_pm_reviews for update to authenticated using (true) with check (true);
drop policy if exists "Allow delete access" on public.supervisor_plan_pm_reviews;
create policy "Allow delete access" on public.supervisor_plan_pm_reviews for delete to authenticated using (true);

alter table if exists public.supervisor_eod_reviews enable row level security;
drop policy if exists "Allow read access" on public.supervisor_eod_reviews;
create policy "Allow read access" on public.supervisor_eod_reviews for select to authenticated using (true);
drop policy if exists "Allow insert access" on public.supervisor_eod_reviews;
create policy "Allow insert access" on public.supervisor_eod_reviews for insert to authenticated with check (true);
drop policy if exists "Allow update access" on public.supervisor_eod_reviews;
create policy "Allow update access" on public.supervisor_eod_reviews for update to authenticated using (true) with check (true);
drop policy if exists "Allow delete access" on public.supervisor_eod_reviews;
create policy "Allow delete access" on public.supervisor_eod_reviews for delete to authenticated using (true);
