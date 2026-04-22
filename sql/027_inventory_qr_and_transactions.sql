-- QR values for inventory scan + transaction log for stock OUT to jobs.
-- Run after sql/015_inventory_items.sql and sql/023_job_costing_materials_equipment.sql.

alter table public.inventory_items
    add column if not exists qr_code_value text;

create unique index if not exists idx_inventory_items_qr_code_value_unique
    on public.inventory_items (qr_code_value)
    where qr_code_value is not null and length(trim(qr_code_value)) > 0;

comment on column public.inventory_items.qr_code_value is 'Unique scan token for checkout / usage (e.g. INV-AB12CD34).';

create table if not exists public.inventory_transactions (
    id uuid primary key default gen_random_uuid(),
    inventory_item_id uuid not null references public.inventory_items (id) on delete restrict,
    qty numeric(14, 4) not null,
    txn_type text not null default 'OUT',
    job_id uuid null references public.jobs (id) on delete set null,
    employee_id uuid null references public.employees (id) on delete set null,
    profile_id uuid null,
    notes text not null default '',
    created_at timestamptz not null default now()
);

create index if not exists idx_inventory_txn_item on public.inventory_transactions (inventory_item_id);
create index if not exists idx_inventory_txn_job on public.inventory_transactions (job_id);
create index if not exists idx_inventory_txn_created on public.inventory_transactions (created_at desc);

comment on table public.inventory_transactions is 'Stock movements; qty negative for OUT from scan/checkout.';
comment on column public.inventory_transactions.qty is 'Signed quantity (negative = consumption from stock).';
comment on column public.inventory_transactions.profile_id is 'Supabase auth profile id when known.';

alter table if exists public.inventory_transactions enable row level security;

drop policy if exists "Allow read access" on public.inventory_transactions;
create policy "Allow read access" on public.inventory_transactions for select to authenticated using (true);

drop policy if exists "Allow insert access" on public.inventory_transactions;
create policy "Allow insert access" on public.inventory_transactions for insert to authenticated with check (true);

drop policy if exists "Allow update access" on public.inventory_transactions;
create policy "Allow update access" on public.inventory_transactions for update to authenticated using (true) with check (true);

drop policy if exists "Allow delete access" on public.inventory_transactions;
create policy "Allow delete access" on public.inventory_transactions for delete to authenticated using (true);
