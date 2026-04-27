-- Tool trailer kit inventory: small tools/items stored inside a parent asset (typically Tool Trailer).

create table if not exists public.asset_kit_items (
  id uuid primary key default gen_random_uuid(),
  parent_asset_id uuid not null references public.assets(id) on delete cascade,
  item_name text not null,
  category text default '',
  quantity numeric(12,2) not null default 1,
  unit_value numeric(12,2) not null default 0,
  total_value numeric(12,2) generated always as (quantity * unit_value) stored,
  replacement_cost numeric(12,2) not null default 0,
  expected_life_days integer,
  last_replaced_at date,
  replacement_count integer not null default 0,
  inventory_item_id uuid null references public.inventory_items(id) on delete set null,
  qr_code_value text default '',
  is_active boolean not null default true,
  notes text default '',
  created_at timestamptz not null default now()
);

create index if not exists asset_kit_items_parent_idx on public.asset_kit_items (parent_asset_id);
create index if not exists asset_kit_items_active_idx on public.asset_kit_items (is_active) where is_active = true;
create index if not exists asset_kit_items_inv_link_idx on public.asset_kit_items (inventory_item_id) where inventory_item_id is not null;

alter table if exists public.asset_kit_items enable row level security;

drop policy if exists "Allow read access" on public.asset_kit_items;
create policy "Allow read access" on public.asset_kit_items for select to authenticated using (true);

drop policy if exists "Allow insert access" on public.asset_kit_items;
create policy "Allow insert access" on public.asset_kit_items for insert to authenticated with check (true);

drop policy if exists "Allow update access" on public.asset_kit_items;
create policy "Allow update access" on public.asset_kit_items for update to authenticated using (true) with check (true);

drop policy if exists "Allow delete access" on public.asset_kit_items;
create policy "Allow delete access" on public.asset_kit_items for delete to authenticated using (true);

