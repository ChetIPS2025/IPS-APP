-- Unified job cost ledger: labor, materials, equipment, subcontract, and PO expenses.
-- Run after jobs (002), employees (008), job_materials/job_equipment (023), inventory (027).

create table if not exists public.job_expenses (
    id uuid primary key default gen_random_uuid(),
    expense_date date null,
    customer_id uuid null references public.customers (id) on delete set null,
    job_id uuid null references public.jobs (id) on delete cascade,
    category text not null default '',
    vendor text not null default '',
    po_number text not null default '',
    invoice_number text not null default '',
    description text not null default '',
    amount numeric(14, 2) not null default 0,
    status text not null default 'Open',
    notes text not null default '',
    entered_by uuid null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_job_expenses_job_id on public.job_expenses (job_id);
create index if not exists idx_job_expenses_expense_date on public.job_expenses (expense_date);

alter table if exists public.employees
    add column if not exists burden_multiplier numeric(8, 4) not null default 1.35;

alter table if exists public.employees
    add column if not exists burdened_hourly_rate numeric(14, 4) null;

comment on column public.employees.burden_multiplier is
    'Multiplier applied to hourly/overtime rates for loaded labor cost when burdened_hourly_rate is not set.';

alter table if exists public.assets
    add column if not exists monthly_rate numeric(14, 4) not null default 0;

create table if not exists public.job_cost_transactions (
    id uuid primary key default gen_random_uuid(),
    job_id uuid not null references public.jobs (id) on delete cascade,
    transaction_date date not null default current_date,
    cost_category text not null default 'other',
    source_type text not null default '',
    source_id text not null default '',
    employee_id uuid null references public.employees (id) on delete set null,
    item_name text not null default '',
    quantity numeric(14, 4) not null default 0,
    unit_cost numeric(14, 4) not null default 0,
    total_cost numeric(14, 2) not null default 0,
    job_number text not null default '',
    notes text not null default '',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint job_cost_transactions_source_unique unique (source_type, source_id)
);

create index if not exists idx_job_cost_txn_job_id on public.job_cost_transactions (job_id);
create index if not exists idx_job_cost_txn_date on public.job_cost_transactions (transaction_date);
create index if not exists idx_job_cost_txn_category on public.job_cost_transactions (cost_category);

comment on table public.job_cost_transactions is
    'Unified job costing ledger — auto-populated from labor, inventory, equipment, and purchasing.';

alter table if exists public.job_expenses enable row level security;
alter table if exists public.job_cost_transactions enable row level security;

drop policy if exists "Allow read access" on public.job_expenses;
create policy "Allow read access" on public.job_expenses for select to authenticated using (true);
drop policy if exists "Allow insert access" on public.job_expenses;
create policy "Allow insert access" on public.job_expenses for insert to authenticated with check (true);
drop policy if exists "Allow update access" on public.job_expenses;
create policy "Allow update access" on public.job_expenses for update to authenticated using (true) with check (true);
drop policy if exists "Allow delete access" on public.job_expenses;
create policy "Allow delete access" on public.job_expenses for delete to authenticated using (true);

drop policy if exists "Allow read access" on public.job_cost_transactions;
create policy "Allow read access" on public.job_cost_transactions for select to authenticated using (true);
drop policy if exists "Allow insert access" on public.job_cost_transactions;
create policy "Allow insert access" on public.job_cost_transactions for insert to authenticated with check (true);
drop policy if exists "Allow update access" on public.job_cost_transactions;
create policy "Allow update access" on public.job_cost_transactions for update to authenticated using (true) with check (true);
drop policy if exists "Allow delete access" on public.job_cost_transactions;
create policy "Allow delete access" on public.job_cost_transactions for delete to authenticated using (true);
