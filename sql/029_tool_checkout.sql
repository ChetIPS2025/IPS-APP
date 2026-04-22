-- Reusable tool checkout: possession + history on public.assets + public.tool_transactions.
-- Run after sql/001_asset_module_tables.sql, sql/008_employees.sql (or 010), and jobs table exists.
--
-- Schema mapping (spec vs existing columns):
--   tool_name        -> assets.asset_name
--   asset_tag        -> assets.asset_id
--   serial_number    -> assets.serial_number (already exists)
--   qr_code_value    -> assets.qr_code_value (already exists)
--   status           -> assets.status (use Available / Checked Out / Maintenance / Lost)
--   current_job_id   -> assets.assigned_job_id (existing FK to jobs)
--   current_holder   -> assets.current_holder_employee_id (new) + assets.assigned_employee kept in sync for display

alter table public.assets
    add column if not exists is_checkout_item boolean not null default false;

alter table public.assets
    add column if not exists current_holder_employee_id uuid null references public.employees (id) on delete set null;

alter table public.assets
    add column if not exists last_checkout_at timestamptz null;

alter table public.assets
    add column if not exists last_checkin_at timestamptz null;

create index if not exists idx_assets_is_checkout_item on public.assets (is_checkout_item)
    where is_checkout_item = true;

create index if not exists idx_assets_checkout_holder on public.assets (current_holder_employee_id)
    where current_holder_employee_id is not null;

comment on column public.assets.is_checkout_item is 'When true, tool uses Tool Checkout page (possession); never deducts inventory qty_on_hand.';
comment on column public.assets.current_holder_employee_id is 'Employee who has the tool while status is Checked Out.';
comment on column public.assets.last_checkout_at is 'Timestamp of last CHECK_OUT transaction.';
comment on column public.assets.last_checkin_at is 'Timestamp of last CHECK_IN transaction.';

create table if not exists public.tool_transactions (
    id uuid primary key default gen_random_uuid(),
    tool_id uuid not null references public.assets (id) on delete cascade,
    transaction_type text not null check (transaction_type in ('CHECK_OUT', 'CHECK_IN')),
    employee_id uuid null references public.employees (id) on delete set null,
    job_id uuid null references public.jobs (id) on delete set null,
    notes text not null default '',
    created_at timestamptz not null default now()
);

create index if not exists idx_tool_txn_tool on public.tool_transactions (tool_id);
create index if not exists idx_tool_txn_created on public.tool_transactions (created_at desc);
create index if not exists idx_tool_txn_type on public.tool_transactions (transaction_type);

comment on table public.tool_transactions is 'Audit log for reusable tool checkout / check-in (separate from inventory_transactions).';

alter table if exists public.tool_transactions enable row level security;

drop policy if exists "Allow read access" on public.tool_transactions;
create policy "Allow read access" on public.tool_transactions for select to authenticated using (true);

drop policy if exists "Allow insert access" on public.tool_transactions;
create policy "Allow insert access" on public.tool_transactions for insert to authenticated with check (true);

drop policy if exists "Allow update access" on public.tool_transactions;
create policy "Allow update access" on public.tool_transactions for update to authenticated using (true) with check (true);

drop policy if exists "Allow delete access" on public.tool_transactions;
create policy "Allow delete access" on public.tool_transactions for delete to authenticated using (true);
