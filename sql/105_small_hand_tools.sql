-- Quantity-based small hand tools (pliers, wrenches, etc.) — no serial number required.

create table if not exists public.small_hand_tools (
    id uuid primary key default gen_random_uuid(),
    tool_name text not null,
    category text not null default 'Other',
    description text not null default '',
    quantity_on_hand numeric(12, 2) not null default 0,
    quantity_expected numeric(12, 2) not null default 0,
    unit text not null default 'EA',
    unit_value numeric(12, 2) not null default 0,
    storage_type text not null default 'Warehouse',
    container_asset_id uuid null references public.assets (id) on delete set null,
    storage_location text not null default '',
    assigned_job_id uuid null references public.jobs (id) on delete set null,
    status text not null default 'Available',
    condition text not null default 'Good',
    notes text not null default '',
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_small_hand_tools_active
    on public.small_hand_tools (is_active) where is_active = true;

create index if not exists idx_small_hand_tools_container
    on public.small_hand_tools (container_asset_id) where container_asset_id is not null;

create index if not exists idx_small_hand_tools_job
    on public.small_hand_tools (assigned_job_id) where assigned_job_id is not null;

create index if not exists idx_small_hand_tools_category on public.small_hand_tools (category);

comment on table public.small_hand_tools is
    'Quantity-tracked hand tools (no serial). May live in tool trailers, shop, warehouse, or on jobs.';

alter table if exists public.small_hand_tools enable row level security;

drop policy if exists "small_hand_tools_all" on public.small_hand_tools;
create policy "small_hand_tools_all"
    on public.small_hand_tools for all to authenticated using (true) with check (true);

insert into public.ips_lookup_values (lookup_table_id, value, sort_order, is_active)
select lt.id, v.val, v.ord, true
from public.ips_lookup_tables lt
cross join (
    values
        ('Pliers', 10),
        ('Screwdrivers', 11),
        ('Wrenches', 12),
        ('Clamps', 13),
        ('Hammers', 14),
        ('Tape Measures', 15),
        ('Levels', 16),
        ('Sockets', 17),
        ('Cutters', 18),
        ('Other', 99)
) as v(val, ord)
where lt.slug = 'asset_categories'
  and not exists (
      select 1
      from public.ips_lookup_values lv
      where lv.lookup_table_id = lt.id
        and lower(lv.value) = lower(v.val)
  );
