-- Tool Kits: named kit containers for small tools/items inside a parent asset (typically Tool Trailer).

create table if not exists public.asset_kits (
  id uuid primary key default gen_random_uuid(),
  asset_id uuid not null references public.assets(id) on delete cascade,
  kit_name text not null,
  description text default '',
  created_at timestamptz not null default now(),
  created_by uuid null references public.profiles(id) on delete set null,
  is_active boolean not null default true
);

create index if not exists asset_kits_asset_idx on public.asset_kits (asset_id);
create index if not exists asset_kits_active_idx on public.asset_kits (is_active) where is_active = true;

alter table if exists public.asset_kits enable row level security;

drop policy if exists "Allow read access" on public.asset_kits;
create policy "Allow read access" on public.asset_kits for select to authenticated using (true);

drop policy if exists "Allow insert access" on public.asset_kits;
create policy "Allow insert access" on public.asset_kits for insert to authenticated with check (true);

drop policy if exists "Allow update access" on public.asset_kits;
create policy "Allow update access" on public.asset_kits for update to authenticated using (true) with check (true);

drop policy if exists "Allow delete access" on public.asset_kits;
create policy "Allow delete access" on public.asset_kits for delete to authenticated using (true);

