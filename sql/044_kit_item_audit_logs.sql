-- Kit item count audits + on-hand / missing tracking for tool trailer kits.
-- Run after sql/038_asset_kit_items.sql, sql/040_asset_kits.sql, sql/041_asset_kit_items_kits.sql.

alter table if exists public.asset_kit_items
    add column if not exists quantity_on_hand numeric(12, 2),
    add column if not exists missing_count numeric(12, 2) not null default 0,
    add column if not exists last_counted_at timestamptz null;

-- Backfill on-hand from expected quantity where not yet counted.
update public.asset_kit_items
set quantity_on_hand = quantity
where quantity_on_hand is null;

comment on column public.asset_kit_items.quantity is 'Expected quantity in kit (canonical expected count).';
comment on column public.asset_kit_items.quantity_on_hand is 'Last verified on-hand count from kit audit.';
comment on column public.asset_kit_items.missing_count is 'Expected minus on-hand from last audit (theft / loss signal).';
comment on column public.asset_kit_items.last_counted_at is 'Timestamp of last kit count / audit.';

create table if not exists public.kit_item_audit_logs (
    id uuid primary key default gen_random_uuid(),
    kit_item_id uuid not null references public.asset_kit_items (id) on delete cascade,
    asset_id uuid not null references public.assets (id) on delete cascade,
    kit_id uuid null references public.asset_kits (id) on delete set null,
    audit_date date not null default (current_date),
    expected_qty numeric(12, 2) not null,
    actual_qty numeric(12, 2) not null,
    missing_qty numeric(12, 2) not null default 0,
    audit_condition text not null default 'OK',
    photo_url text not null default '',
    notes text not null default '',
    counted_by text not null default '',
    created_at timestamptz not null default now()
);

create index if not exists kit_item_audit_logs_kit_item_idx on public.kit_item_audit_logs (kit_item_id, created_at desc);
create index if not exists kit_item_audit_logs_asset_idx on public.kit_item_audit_logs (asset_id, created_at desc);
create index if not exists kit_item_audit_logs_kit_idx on public.kit_item_audit_logs (kit_id, created_at desc);

comment on table public.kit_item_audit_logs is 'Per-line kit count audits (theft prevention / proof).';
comment on column public.kit_item_audit_logs.audit_condition is 'OK | Missing | Damaged (UI condition).';

alter table if exists public.kit_item_audit_logs enable row level security;

drop policy if exists "Allow read access" on public.kit_item_audit_logs;
create policy "Allow read access" on public.kit_item_audit_logs for select to authenticated using (true);

drop policy if exists "Allow insert access" on public.kit_item_audit_logs;
create policy "Allow insert access" on public.kit_item_audit_logs for insert to authenticated with check (true);

drop policy if exists "Allow update access" on public.kit_item_audit_logs;
create policy "Allow update access" on public.kit_item_audit_logs for update to authenticated using (true) with check (true);

drop policy if exists "Allow delete access" on public.kit_item_audit_logs;
create policy "Allow delete access" on public.kit_item_audit_logs for delete to authenticated using (true);
