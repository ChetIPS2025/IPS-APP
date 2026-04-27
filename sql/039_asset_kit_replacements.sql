-- Kit item replacement history + cost tracking

create table if not exists public.asset_kit_replacements (
  id uuid primary key default gen_random_uuid(),
  parent_asset_id uuid not null references public.assets(id) on delete cascade,
  kit_item_id uuid not null references public.asset_kit_items(id) on delete cascade,
  replacement_date date not null default (now()::date),
  quantity_replaced numeric(12,2) not null default 1,
  unit_cost numeric(12,2) not null default 0,
  total_cost numeric(12,2) generated always as (quantity_replaced * unit_cost) stored,
  reason text default '',
  replaced_by uuid null references public.profiles(id) on delete set null,
  job_id uuid null references public.jobs(id) on delete set null,
  notes text default '',
  created_at timestamptz not null default now()
);

create index if not exists asset_kit_repl_parent_idx on public.asset_kit_replacements (parent_asset_id, replacement_date desc);
create index if not exists asset_kit_repl_item_idx on public.asset_kit_replacements (kit_item_id, replacement_date desc);

alter table if exists public.asset_kit_replacements enable row level security;

drop policy if exists "Allow read access" on public.asset_kit_replacements;
create policy "Allow read access" on public.asset_kit_replacements for select to authenticated using (true);

drop policy if exists "Allow insert access" on public.asset_kit_replacements;
create policy "Allow insert access" on public.asset_kit_replacements for insert to authenticated with check (true);

drop policy if exists "Allow update access" on public.asset_kit_replacements;
create policy "Allow update access" on public.asset_kit_replacements for update to authenticated using (true) with check (true);

drop policy if exists "Allow delete access" on public.asset_kit_replacements;
create policy "Allow delete access" on public.asset_kit_replacements for delete to authenticated using (true);

