-- Mobile inventory QR scan: tokens, allocation columns, extended transaction audit.
-- Run after sql/027_inventory_qr_and_transactions.sql and sql/030_inventory_txn_scan_audit.sql.

alter table public.inventory_items
    add column if not exists qr_token text,
    add column if not exists quantity_checked_out numeric not null default 0,
    add column if not exists quantity_allocated numeric not null default 0;

create unique index if not exists idx_inventory_items_qr_token_unique
    on public.inventory_items (qr_token)
    where qr_token is not null and length(trim(qr_token)) > 0;

comment on column public.inventory_items.qr_token is 'Secret token for mobile QR deep links; validated on scan.';
comment on column public.inventory_items.quantity_checked_out is 'Stock checked out but not yet allocated to a job.';
comment on column public.inventory_items.quantity_allocated is 'Stock issued/allocated to jobs.';

alter table public.inventory_transactions
    add column if not exists transaction_type text,
    add column if not exists quantity numeric,
    add column if not exists unit text,
    add column if not exists previous_quantity numeric,
    add column if not exists new_quantity numeric,
    add column if not exists scanned_by_phone text,
    add column if not exists phone_verified boolean not null default false,
    add column if not exists source text default 'qr_scan',
    add column if not exists device_info text,
    add column if not exists scanned_by_employee_id uuid references public.employees (id) on delete set null;

create index if not exists idx_inventory_transactions_inventory_id
    on public.inventory_transactions (inventory_item_id);

create index if not exists idx_inventory_transactions_job_id
    on public.inventory_transactions (job_id);

create index if not exists idx_inventory_transactions_created_at
    on public.inventory_transactions (created_at desc);

-- TODO: tighten RLS for anonymous QR inserts (token + rate limit) when public scanning is enabled.
alter table if exists public.inventory_transactions enable row level security;

drop policy if exists "inventory_transactions_all" on public.inventory_transactions;
create policy "inventory_transactions_all"
    on public.inventory_transactions
    for all
    to authenticated
    using (true)
    with check (true);
