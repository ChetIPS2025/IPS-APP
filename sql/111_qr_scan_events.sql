-- QR scan activity log: every scan/open attempt, separate from stock transactions.
-- Run after sql/027, sql/029, sql/030, sql/110.

create table if not exists public.qr_scan_events (
    id uuid primary key default gen_random_uuid(),
    created_at timestamptz not null default now(),
    qr_value text not null default '',
    item_type text not null default 'unknown',
    item_name text not null default '',
    inventory_item_id uuid null references public.inventory_items (id) on delete set null,
    asset_id uuid null references public.assets (id) on delete set null,
    result text not null default 'opened',
    action_taken text null,
    job_id uuid null references public.jobs (id) on delete set null,
    destination_type text null,
    scanned_by_user_id text null,
    scanned_by_name text null,
    scanned_by_phone text null,
    employee_id uuid null references public.employees (id) on delete set null,
    device_label text null,
    source text not null default 'qr_scan',
    error_message text null,
    inventory_transaction_id uuid null,
    tool_transaction_id uuid null,
    quantity numeric(14, 4) null,
    unit text null
);

create index if not exists idx_qr_scan_events_created
    on public.qr_scan_events (created_at desc);

create index if not exists idx_qr_scan_events_qr_value
    on public.qr_scan_events (qr_value);

create index if not exists idx_qr_scan_events_inventory_item
    on public.qr_scan_events (inventory_item_id)
    where inventory_item_id is not null;

create index if not exists idx_qr_scan_events_asset
    on public.qr_scan_events (asset_id)
    where asset_id is not null;

create index if not exists idx_qr_scan_events_result
    on public.qr_scan_events (result);

comment on table public.qr_scan_events is
    'QR scan/open audit — tracks opens, successes, failures, and unknown codes separately from inventory_transactions.';

comment on column public.qr_scan_events.result is
    'opened = code resolved and form shown; success = action completed; failed = error; unknown_item = no match.';

alter table if exists public.qr_scan_events enable row level security;

drop policy if exists qr_scan_events_select on public.qr_scan_events;
create policy qr_scan_events_select on public.qr_scan_events
    for select to authenticated using (true);

drop policy if exists qr_scan_events_insert on public.qr_scan_events;
create policy qr_scan_events_insert on public.qr_scan_events
    for insert to authenticated with check (true);
