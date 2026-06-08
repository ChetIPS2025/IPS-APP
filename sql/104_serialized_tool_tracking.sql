-- Serialized cordless tool tracking (Milwaukee tools in Tool Trailers).
-- Reuses assets + asset_kit_items + tool_transactions; adds container/audit timestamps.

alter table public.assets
    add column if not exists is_serialized_tool boolean not null default false,
    add column if not exists current_container_asset_id uuid null references public.assets (id) on delete set null,
    add column if not exists last_seen_at timestamptz null,
    add column if not exists last_audited_at timestamptz null;

create index if not exists idx_assets_serialized_tool on public.assets (is_serialized_tool)
    where is_serialized_tool = true;

create index if not exists idx_assets_current_container on public.assets (current_container_asset_id)
    where current_container_asset_id is not null;

create unique index if not exists uq_assets_serialized_serial
    on public.assets (lower(trim(serial_number)))
    where is_serialized_tool = true
      and coalesce(trim(serial_number), '') <> ''
      and coalesce(is_active, true) = true;

comment on column public.assets.is_serialized_tool is
    'Individual serialized cordless tool (drill, impact, etc.) tracked by serial number.';
comment on column public.assets.current_container_asset_id is
    'Tool Trailer or kit parent asset that currently stores this tool.';
comment on column public.assets.last_seen_at is
    'Last scan, checkout, check-in, or audit sighting.';
comment on column public.assets.last_audited_at is
    'Last time this tool was verified present during a trailer audit.';

-- current_employee_id -> current_holder_employee_id (029)
-- current_job_id -> assigned_job_id (077/029)
-- current_operator -> assigned_employee / operator (existing)

insert into public.ips_lookup_values (lookup_table_id, value, sort_order, is_active)
select lt.id, v.val, v.ord, true
from public.ips_lookup_tables lt
cross join (
    values
        ('Tool Trailer', 45),
        ('Drill', 10),
        ('Impact', 11),
        ('Grinder', 12),
        ('Saw', 13),
        ('Rotary Hammer', 14),
        ('Light', 15),
        ('Charger', 16),
        ('Battery', 17)
) as v(val, ord)
where lt.slug = 'asset_categories'
  and not exists (
      select 1
      from public.ips_lookup_values lv
      where lv.lookup_table_id = lt.id
        and lower(lv.value) = lower(v.val)
  );
