-- Asset tab classification: equipment | serialized | quantity (Small Tools).

alter table public.assets
    add column if not exists tracking_type text;

comment on column public.assets.tracking_type is
    'Which Assets tab owns this record: equipment, serialized, or quantity (small hand tools).';

create index if not exists idx_assets_tracking_type
    on public.assets (tracking_type) where tracking_type is not null;

alter table public.small_hand_tools
    add column if not exists source_asset_id uuid null references public.assets (id) on delete set null;

create unique index if not exists uq_small_hand_tools_source_asset
    on public.small_hand_tools (source_asset_id)
    where source_asset_id is not null and is_active = true;

comment on column public.small_hand_tools.source_asset_id is
    'Original assets row when reclassified from Equipment to Small Tools (quantity tracking).';

-- Backfill existing rows
update public.assets
set tracking_type = 'serialized'
where coalesce(tracking_type, '') = ''
  and is_serialized_tool = true;

update public.assets
set tracking_type = 'equipment'
where coalesce(tracking_type, '') = ''
  and (is_kit = true or coalesce(kit_type, '') <> '');

update public.assets
set tracking_type = 'serialized'
where coalesce(tracking_type, '') = ''
  and is_checkout_item = true
  and coalesce(trim(serial_number), '') <> '';

update public.assets
set tracking_type = 'equipment'
where coalesce(tracking_type, '') = '';
