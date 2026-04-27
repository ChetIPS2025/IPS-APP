-- Link kit items to named kits (optional/nullable for backward compatibility).

alter table if exists public.asset_kit_items
  add column if not exists kit_id uuid null references public.asset_kits(id) on delete set null;

create index if not exists asset_kit_items_kit_idx on public.asset_kit_items (kit_id) where kit_id is not null;

