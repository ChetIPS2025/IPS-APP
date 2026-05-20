-- =============================================================================
-- 003_estimates.sql — Estimates module
-- Depends on: 001_core.sql, 002_jobs.sql
-- =============================================================================

create table if not exists public.estimates (
    id uuid primary key default gen_random_uuid(),
    customer_id uuid references public.customers (id) on delete set null,
    job_id uuid references public.jobs (id) on delete set null,
    quote_number text,
    estimate_number text generated always as (quote_number) stored,
    customer_name text not null default '',
    project_name text not null default '',
    job_name text not null default '',
    status text not null default 'Draft',
    estimate_date date,
    expiration_date date,
    valid_through date generated always as (expiration_date) stored,
    prepared_by_name text not null default '',
    created_by text not null default '',
    subtotal numeric(14, 2) not null default 0,
    labor_total numeric(14, 2) not null default 0,
    material_total numeric(14, 2) not null default 0,
    equipment_total numeric(14, 2) not null default 0,
    markup numeric(14, 2) not null default 0,
    tax numeric(14, 2) not null default 0,
    total numeric(14, 2) not null default 0,
    grand_total numeric(14, 2) generated always as (total) stored,
    notes text not null default '',
    revision_number int not null default 1,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_estimates_customer_id on public.estimates (customer_id);
create index if not exists idx_estimates_job_id on public.estimates (job_id);
create index if not exists idx_estimates_status on public.estimates (status);
create index if not exists idx_estimates_quote_number on public.estimates (quote_number);
create index if not exists idx_estimates_estimate_date on public.estimates (estimate_date);

create unique index if not exists uq_estimates_quote_number
    on public.estimates (quote_number)
    where quote_number is not null and trim(quote_number) <> '';

drop trigger if exists trg_estimates_updated_at on public.estimates;
create trigger trg_estimates_updated_at
    before update on public.estimates
    for each row execute function public.ips_set_updated_at();

-- Link jobs.estimate_id (bidirectional)
do $$
begin
    if not exists (
        select 1 from information_schema.table_constraints
        where constraint_schema = 'public'
          and table_name = 'jobs'
          and constraint_name = 'jobs_estimate_id_fkey'
    ) then
        alter table public.jobs
            add constraint jobs_estimate_id_fkey
            foreign key (estimate_id) references public.estimates (id) on delete set null;
    end if;
exception when others then
    null;
end $$;

-- -----------------------------------------------------------------------------
-- estimate_line_items (materials tab + estimate_materials page)
-- -----------------------------------------------------------------------------
create table if not exists public.estimate_line_items (
    id uuid primary key default gen_random_uuid(),
    estimate_id uuid not null references public.estimates (id) on delete cascade,
    inventory_item_id uuid,
    item_number text not null default '',
    description text not null default '',
    category text not null default '',
    qty numeric not null default 0,
    unit text not null default 'EA',
    unit_cost numeric not null default 0,
    total_cost numeric not null default 0,
    markup numeric not null default 0,
    vendor text not null default '',
    notes text not null default '',
    sort_order int not null default 0,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_estimate_line_items_estimate
    on public.estimate_line_items (estimate_id, sort_order);

drop trigger if exists trg_estimate_line_items_updated_at on public.estimate_line_items;
create trigger trg_estimate_line_items_updated_at
    before update on public.estimate_line_items
    for each row execute function public.ips_set_updated_at();

-- -----------------------------------------------------------------------------
-- estimate_labor_lines
-- -----------------------------------------------------------------------------
create table if not exists public.estimate_labor_lines (
    id uuid primary key default gen_random_uuid(),
    estimate_id uuid not null references public.estimates (id) on delete cascade,
    description text not null default '',
    labor_type text not null default 'ST',
    hours numeric not null default 0,
    rate numeric not null default 0,
    total numeric not null default 0,
    sort_order int not null default 0,
    created_at timestamptz not null default now()
);

create index if not exists idx_estimate_labor_estimate
    on public.estimate_labor_lines (estimate_id, sort_order);

-- -----------------------------------------------------------------------------
-- estimate_activity_log
-- -----------------------------------------------------------------------------
create table if not exists public.estimate_activity_log (
    id uuid primary key default gen_random_uuid(),
    estimate_id uuid not null references public.estimates (id) on delete cascade,
    activity_type text not null default 'update',
    description text not null default '',
    created_by uuid references public.profiles (id) on delete set null,
    created_at timestamptz not null default now()
);

create index if not exists idx_estimate_activity_estimate
    on public.estimate_activity_log (estimate_id, created_at desc);

-- -----------------------------------------------------------------------------
-- RLS
-- -----------------------------------------------------------------------------
alter table public.estimates enable row level security;
alter table public.estimate_line_items enable row level security;
alter table public.estimate_labor_lines enable row level security;
alter table public.estimate_activity_log enable row level security;

drop policy if exists estimates_select on public.estimates;
create policy estimates_select on public.estimates for select to authenticated using (true);
drop policy if exists estimates_write on public.estimates;
create policy estimates_write on public.estimates for all to authenticated using (true) with check (true);

drop policy if exists estimate_line_items_all on public.estimate_line_items;
create policy estimate_line_items_all on public.estimate_line_items for all to authenticated using (true) with check (true);

drop policy if exists estimate_labor_lines_all on public.estimate_labor_lines;
create policy estimate_labor_lines_all on public.estimate_labor_lines for all to authenticated using (true) with check (true);

drop policy if exists estimate_activity_log_all on public.estimate_activity_log;
create policy estimate_activity_log_all on public.estimate_activity_log for all to authenticated using (true) with check (true);

comment on table public.estimates is 'Quotes / proposals (IPS Estimates module).';
comment on column public.estimates.quote_number is 'App UI: estimate_number.';
comment on table public.estimate_line_items is 'Material and custom lines (Estimate Materials page).';
