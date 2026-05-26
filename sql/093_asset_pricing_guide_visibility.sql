-- =============================================================================
-- 093_asset_pricing_guide_visibility.sql — Control which assets appear on PG
-- Safe to re-run.
-- =============================================================================

alter table if exists public.assets
    add column if not exists include_in_pricing_guide boolean not null default false;

comment on column public.assets.include_in_pricing_guide is
    'When false, the asset stays in Assets but is hidden from Pricing Guide and estimates.';

-- Existing linked assets remain billable until explicitly turned off.
update public.assets a
set include_in_pricing_guide = true
where coalesce(a.pricing_guide_id::text, a.pricing_item_id::text, '') <> '';

update public.assets a
set include_in_pricing_guide = true
from public.pricing_guide_items p
where coalesce(a.include_in_pricing_guide, false) = false
  and (
      p.linked_asset_id = a.id
      or p.asset_id = a.id
  );

create index if not exists idx_assets_include_in_pricing_guide
    on public.assets (include_in_pricing_guide);
